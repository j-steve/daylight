from flask import Flask, make_response, redirect, render_template, request, url_for
import robin_auth
import orders

app = Flask('app')

@app.template_filter()
def format_currency(value):
  if not value: return ''
  value = float(value)
  return "${:,.2f}".format(value)

@app.template_filter()
def format_percent(value):
  if not value: return ''
  value = float(value) * 100
  return "{:,.0f}%".format(value)

@app.template_filter()
def format_date(value):
  if not value: return ''
  return value.strftime('%Y-%m-%d')

@app.route('/login')
def login():
  return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
  username = request.form['username']
  password = request.form['password']
  try:
    token, challenge_id = robin_auth.login(username, password)
    if token:
      return _redirect_with_token(token, 'data')
    else:
      return render_template('sms_code.html', username=username, password=password, challenge_id=challenge_id)
  except robin_auth.AuthError:
    return redirect(url_for('login'))

@app.route('/sms-code', methods=['POST'])
def sms_code_post():
  token = robin_auth.send_challenge_response(
    request.form['username'],
    request.form['password'],
    request.form['challenge_id'],
    request.form['sms_code'])
  return _redirect_with_token(token, 'data')

def _redirect_with_token(token, redirect_to):
  resp = make_response(redirect(url_for('data')))
  resp.set_cookie('token', token, max_age=robin_auth.TOKEN_DURATION)
  return resp

@app.route('/data')
def data():
  token = request.cookies.get('token')
  if not token:
    return redirect(url_for('login'))
  robin_auth.set_token(token)
  transactions = orders.retrieve_all_orders()
  return render_template('data.html', transactions=transactions)

@app.route('/logout',)
def logout():
  resp = make_response(redirect(url_for('login')))
  resp.delete_cookie('token')
  return resp

@app.route('/')
def home():
  return redirect(url_for('login'))
  return render_template('home.html')

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080, debug=True)