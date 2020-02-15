from flask import Flask, redirect, render_template, request, url_for
import robin_stocks
import robin_auth

app = Flask('app')

@app.route('/login')
def login():
  return render_template('login.html')

@app.route('/sms-code', methods=['POST'])
def sms_code():
  username = request.form['username']
  password = request.form['password']
  try:
    requires_challenge, challenge_id = robin_auth.login(username, password)
    if requires_challenge:
      return render_template('sms_code.html', username = username, 
                            password = password, challenge_id = challenge_id)
    else:
      return redirect(url_for('data'))
  except robin_auth.AuthError as e:
    return redirect(url_for('login'))

@app.route('/sms-code', methods=['POST'])
def sms_code_post():
  robin_auth.send_challenge_response(
    request.form['username'],
    request.form['password'],
    request.form['challenge_id'],
    request.form['sms_code'])
  return redirect(url_for('data'))

@app.route('/data',)
def data():
  transactions = robin_stocks.orders.get_all_orders()
  return render_template('data.html', transactions = transactions)

@app.route('/')
def home():
  return redirect(url_for('login'))
  return render_template('home.html')

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080, debug=True)