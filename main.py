from flask import Flask, redirect, render_template, url_for
app = Flask('app')

import robin_stocks

# password = input('Password: ')
# robin_stocks.login('steve5805@gmail.com', password)
# orders = robin_stocks.orders.get_all_orders()

@app.route('/login')
def login():
  return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_submit():
  return redirect(url_for('sms_code'))

@app.route('/sms-code')
def sms_code():
  return render_template('sms_code.html')

@app.route('/sms-code', methods=['POST'])
def sms_cod_submit():
  return redirect(url_for('data'))

@app.route('/data')
def data():
  return render_template('data.html', transactions = [{"price": 5}])

@app.route('/')
def hello_world():
  return redirect(url_for('login'))
  # result = '<table><tr><th>Price</th><th>Quantity</th><th>Date</th></tr>'
  # for o in orders:
  #   result += '<tr><td>{price}</td><td>{quantity}</td><td>{date}</td></tr>'.format(price=o.get('price', ''), quantity=o.get('quantity', ''), date=o.get('last_transaction_at', ''))
  # return result + '</table>'
  return render_template('home.html')

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080, debug=True)