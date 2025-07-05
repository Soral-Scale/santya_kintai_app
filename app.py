from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response
import pandas as pd
import calendar
from datetime import datetime
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
)
import os

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-very-secret-key'
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False  # 本番環境ではTrueに
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False

jwt = JWTManager(app)

# =======================================
# 設定・共通処理
# =======================================

DATA_DIR = 'data'  # データフォルダをまとめる場合

def load_excel(filename):
    return pd.read_excel(os.path.join(DATA_DIR, filename))


def make_calendar(year: int, month: int):
    cal = calendar.Calendar(firstweekday=6)  # 日曜始まり（6 = Sunday）
    month_days = cal.itermonthdays(year, month)
    weeks = []
    week = []
    for day in month_days:
        week.append(day)
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        week += [0] * (7 - len(week))
        weeks.append(week)
    return weeks

# =======================================
# ルーティング
# =======================================

@app.route('/')
def splash():
    return render_template('splash.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        try:
            df = load_excel('users.xlsx')
            df['user_id'] = df['user_id'].astype(str)
            df['password'] = df['password'].astype(str)

            user = df[(df['user_id'] == user_id) & (df['password'] == password)]
            if not user.empty:
                access_token = create_access_token(identity=user_id)
                response = make_response(redirect(url_for('shift')))
                set_access_cookies(response, access_token)
                return response
            else:
                return render_template('login.html', error='ユーザーIDまたはパスワードが違います。')

        except Exception as e:
            return render_template('login.html', error='エラーが発生しました')

    return render_template('login.html')


@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('login')))
    unset_jwt_cookies(response)
    return response


@app.route('/shift/', defaults={'year': None, 'month': None})
@app.route('/shift/<int:year>/<int:month>')
@jwt_required()
def shift(year, month):
    user_id = get_jwt_identity()
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    weeks = make_calendar(year, month)
    return render_template('shift.html', user_id=user_id, year=year, month=month, weeks=weeks)


@app.route('/get_shift', methods=['GET'])
@jwt_required()
def get_shift():
    user_id = get_jwt_identity()
    date = request.args.get('date')
    try:
        df = load_excel('shifts.xlsx')
        record = df[(df['user_id'] == user_id) & (df['date'] == date)]
        if not record.empty:
            row = record.iloc[0]
            work_time = row.get("work_time")
            if pd.isna(work_time) or (isinstance(work_time, str) and work_time.strip() == ""):
                work_time = None
            return jsonify({"shift_code": row["shift_code"], "work_time": work_time})
        else:
            return jsonify({"message": "No shift data found"}), 404
    except Exception as e:
        return jsonify({"error": "データ取得に失敗しました。"}), 500


@app.route("/attendance", methods=["GET", "POST"])
@jwt_required()
def attendance():
    user_id = str(get_jwt_identity())
    if request.method == "POST":
        date = request.form.get("date")
        status = request.form.get("status")
        memo = request.form.get("memo", "").strip()

        if not date or not status or not memo:
            return redirect(url_for('attendance', error=1))

        try:
            df = load_excel('notices.xlsx')
            today_str = datetime.now().strftime('%Y-%m-%d')
            new_notice = {
                'user_id': user_id,
                'title': "勤怠連絡受付けました。",
                'message': f"勤務日：{date}　内容：{status}　\n詳細：{memo}",
                'date': today_str,
                'read_flag': 0
            }
            df = pd.concat([df, pd.DataFrame([new_notice])], ignore_index=True)
            df.to_excel(os.path.join(DATA_DIR, 'notices.xlsx'), index=False)
        except Exception as e:
            print(f"通知追加エラー: {e}")
        return redirect(url_for('attendance', sent=1))

    sent = request.args.get('sent') == '1'
    error = request.args.get('error') == '1'
    return render_template("attendance.html", sent=sent, error=error)


@app.route('/notices')
@jwt_required()
def notice_page():
    user_id = get_jwt_identity()
    try:
        df = load_excel('notices.xlsx')
        df['user_id'] = df['user_id'].astype(str)
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        notices = df[df['user_id'] == user_id].sort_values(by='date', ascending=False)
        return render_template('notice.html', notices=notices.to_dict(orient='records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_notices', methods=['GET'])
@jwt_required()
def get_notices():
    user_id = get_jwt_identity()
    try:
        df = load_excel('notices.xlsx')
        df['user_id'] = df['user_id'].astype(str)
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        notices = df[(df['user_id'] == user_id) & (df['read_flag'] == 0)]
        return jsonify(notices[['title', 'message', 'date']].to_dict(orient='records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/mark_notice_read', methods=['POST'])
@jwt_required()
def mark_notice_read():
    user_id = get_jwt_identity()
    try:
        data = request.get_json()
        title = data.get('title')
        df = load_excel('notices.xlsx')
        df['user_id'] = df['user_id'].astype(str)
        mask = (df['user_id'] == user_id) & (df['title'] == title)
        if df[mask].empty:
            return jsonify({"message": "Notice not found"}), 404
        df.loc[mask, 'read_flag'] = 1
        df.to_excel(os.path.join(DATA_DIR, 'notices.xlsx'), index=False)
        return jsonify({"message": "Notice marked as read"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_all_notices', methods=['GET'])
@jwt_required()
def get_all_notices():
    user_id = get_jwt_identity()
    try:
        df = load_excel('notices.xlsx')
        df['user_id'] = df['user_id'].astype(str)
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        notices = df[df['user_id'] == user_id]
        return jsonify(notices[['title', 'message', 'date', 'read_flag']].to_dict(orient='records'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)