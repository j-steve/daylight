from flask import Flask, render_template
app = Flask('app')

import robin_stocks

# password = input('Password: ')
# robin_stocks.login('steve5805@gmail.com', password)
# orders = robin_stocks.orders.get_all_orders()

@app.route('/login')
def login():
  return render_template('login.html')

@app.route('/')
def hello_world():
  # result = '<table><tr><th>Price</th><th>Quantity</th><th>Date</th></tr>'
  # for o in orders:
  #   result += '<tr><td>{price}</td><td>{quantity}</td><td>{date}</td></tr>'.format(price=o.get('price', ''), quantity=o.get('quantity', ''), date=o.get('last_transaction_at', ''))
  # return result + '</table>'
  return render_template('home.html')

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080, debug=True)