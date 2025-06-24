from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
import requests

API_URL = 'http://localhost:5000'  # Flask APIのURL（スマホ実機ならIPに）

class LoginScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.token = None

        self.add_widget(Label(text='User ID'))
        self.user_input = TextInput(multiline=False)
        self.add_widget(self.user_input)

        self.add_widget(Label(text='Password'))
        self.pass_input = TextInput(password=True, multiline=False)
        self.add_widget(self.pass_input)

        self.login_btn = Button(text='Login')
        self.login_btn.bind(on_press=self.login)
        self.add_widget(self.login_btn)

        self.result_label = Label(text='')
        self.add_widget(self.result_label)

    def login(self, instance):
        user_id = self.user_input.text.strip()
        password = self.pass_input.text.strip()

        try:
            res = requests.post(f'{API_URL}/login', json={
                'user_id': user_id,
                'password': password
            })
            if res.status_code == 200:
                self.token = res.json()['access_token']
                self.result_label.text = f'Login success as {user_id}'
                self.clear_widgets()
                self.show_shift_screen()
            else:
                self.result_label.text = 'Login failed'
        except Exception as e:
            self.result_label.text = f'Error: {str(e)}'

    def show_shift_screen(self):
        self.add_widget(Label(text='Enter date (YYYY-MM-DD)'))
        self.date_input = TextInput(multiline=False)
        self.add_widget(self.date_input)

        self.get_shift_btn = Button(text='Get Shift')
        self.get_shift_btn.bind(on_press=self.get_shift)
        self.add_widget(self.get_shift_btn)

        self.shift_result = Label(text='')
        self.add_widget(self.shift_result)

    def get_shift(self, instance):
        date = self.date_input.text.strip()
        headers = {'Authorization': f'Bearer {self.token}'}

        try:
            res = requests.get(f'{API_URL}/get_shift', params={'date': date}, headers=headers)
            if res.status_code == 200:
                shift_data = res.json()
                self.shift_result.text = f"Shift: {shift_data['shift_code']}\nTime: {shift_data['work_time']}"
            else:
                self.shift_result.text = f"No shift found for {date}"
        except Exception as e:
            self.shift_result.text = f'Error: {str(e)}'

class ShiftApp(App):
    def build(self):
        return LoginScreen()

if __name__ == '__main__':
    ShiftApp().run()