from collections import defaultdict
import datetime
import robin_stocks
import sqlite3

def parse(order_data):
  orders = []
  for order in order_data:
    if order['state'] != 'filled':
      continue
    
    instrument = None
    with sqlite3.connect('daylight.db') as db_conn:
      db_conn.row_factory = sqlite3.Row
      instrument = _load_instrument(db_conn, order['instrument'])
    for execution in order['executions']:
      orders.append(Order(order, execution, instrument))
  # Compute profit/loss for each sale.
  dividends = robin_stocks.helper.request_get(
    robin_stocks.urls.dividends(), 'pagination')
  orders.sort(key=lambda x: x.timestamp)
  orders.reverse()
  transactions = defaultdict(lambda: [])
  for o in orders:
    if o.type == 'sell':
          # May be no buy transaction, if this was a free robinhood stock.
      for i in range(o.quantity):
        transactions[o.symbol].append(o)
    elif o.type == 'buy':
      o.profit = 0
      o.dividend_profit = 0
      sale_transactions = []
      sale_time = None
      current_share_price = None
      for i in range(o.quantity):
        dividend_profit = 0
        share_profit = 0 - o.share_price
        sale = None
        if transactions[o.symbol]:
          sale = transactions[o.symbol].pop(-1)
          share_profit += sale.share_price - sale.fees
          sale_time = sale.timestamp
        else:
          if not current_share_price:
            current_share_price = robin_stocks.stocks.get_latest_price(o.symbol)[0]
          share_profit += float(current_share_price)
          sale_time = datetime.datetime.now()
        for dividend in dividends:
          dividend_date = datetime.datetime.strptime(dividend['record_date'], '%Y-%m-%d')
          if o.instrument_url == dividend['instrument'] and o.timestamp < dividend_date and (not sale or sale.timestamp > dividend_date):
            dividend_profit = float(dividend['rate'])
        o.profit += share_profit
        o.dividend_profit += dividend_profit
        held_days = (sale_time - o.timestamp).total_seconds() / 60 / 24
        sale_transactions.append((share_profit + dividend_profit) / o.share_price / held_days)
      print(sale_transactions)
      o.total_profit_per_dollar = o.profit / o.total_price
      o.total_profit_per_dollar_per_day = sum(sale_transactions)
  return orders

def _load_instrument(db_conn, url):
  cursor = db_conn.cursor()
  cursor.execute('CREATE TABLE IF NOT EXISTS Instruments(url TEXT PRIMARY KEY NOT NULL, symbol VARCHAR(5) NOT NULL)')
  cursor.execute('SELECT symbol FROM Instruments WHERE url = "{}"'.format(url))
  result = cursor.fetchall()
  if result:
    return result[0]
  else:
    instrument = robin_stocks.helper.request_get(url)
    cursor.execute('INSERT INTO Instruments VALUES("{}", "{}")'.format(url, instrument['symbol']))
    return instrument

class Order(object):
  def __init__(self, order, execution, instrument):
    self.id = order['id']
    self.instrument_url = order['instrument']
    self.symbol = instrument['symbol']
    self.quantity = int(float(execution['quantity']))
    self.share_price = float(execution['price'])
    self.total_price = self.quantity * self.share_price
    self.fees = float(order['fees']) / int(float(order['quantity']))
    self.type = order['side'] # buy or sell
    self.timestamp = self._parse_datetime(execution['timestamp'])
    if self.type == 'sell':
      self.fees_computed = 0.00002 * self.total_price + 0.000119 * self.quantity + 0.02
      self.fees_computed = round(self.fees_computed, 2)
    self.profit = None
    self.dividend_profit = None
    self.sale_transactions = None
    self.total_profit_per_dollar = None
    self.total_profit_per_dollar_per_day = None

  def _parse_datetime(self, date_string):
    try:
      return datetime.datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
      return datetime.datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ')