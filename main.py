from flask import Flask, redirect, render_template, request, url_for
import robin_stocks
import robin_auth
import orders

app = Flask('app')

@app.template_filter()
def currency_format(value):
    if not value: return ''
    value = float(value)
    return "${:,.2f}".format(value)

@app.template_filter()
def percent(value):
    if not value: return ''
    value = float(value) * 100
    return "{:,.0f}%".format(value)

@app.template_filter()
def cents(value):
    if not value: return ''
    value = float(value) * 100
    return "{:,.3f}¢".format(value)

@app.route('/login')
def login():
  return render_template('login.html')

@app.route('/login', methods=['POST'])
def sms_code():
  username = request.form['username']
  password = request.form['password']
  try:
    token, challenge_id = robin_auth.login(username, password)
    if token:
      return redirect(url_for('data', token=token))
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
  return redirect(url_for('data', token=token))

@app.route('/data',)
def data():
  token = request.args.get('token', None)
  if not token:
    return redirect(url_for('login'))
  robin_auth.set_token(token)
  transactions = orders.parse(robin_stocks.orders.get_all_orders())
  return render_template('data.html', transactions=transactions)

@app.route('/')
def home():
  return redirect(url_for('login'))
  return render_template('home.html')

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080, debug=True)