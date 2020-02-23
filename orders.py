from collections import defaultdict
from datetime import datetime
import pytz
import robin_stocks
import sqlite3

def retrieve_all_orders():
  orders = list(_load_stock_orders())
  # orders.extend(_load_crypto_orders())
  orders.sort(key=lambda x: x.timestamp, reverse=True)
  _compute_profit(orders)
  return orders

def _load_stock_orders():
  for order in robin_stocks.orders.get_all_orders():
    if order['state'] != 'filled':
      continue
    instrument = None
    with sqlite3.connect('daylight.db') as db_conn:
      db_conn.row_factory = sqlite3.Row
      instrument = _load_instrument(db_conn, order['instrument'])
    for execution in order['executions']:
      yield Execution(order, execution, instrument['symbol'])

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

def _load_crypto_orders():
  crypto_orders = robin_stocks.helper.request_get(
    robin_stocks.urls.order_crypto(), 'pagination')
  for order in crypto_orders:
    order['instrument'] = order['currency_pair_id']
    order['fees'] = 0
    if order['state'] != 'filled':
      continue
    for execution in order['executions']:
      execution['price'] = execution['effective_price']
      yield Execution(order, execution, 'CRYPTO')

def _compute_profit(orders):
  dividends = robin_stocks.helper.request_get(
    robin_stocks.urls.dividends(), 'pagination')
  transactions = defaultdict(lambda: [])
  for o in orders:
    if o.type == 'sell':
      # May be no buy transaction, if this was a free robinhood stock.
      for i in range(o.quantity):
        transactions[o.symbol].append(o)
    elif o.type == 'buy':
      current_share_price = None
      for i in range(o.quantity):
        sale = None
        if transactions[o.symbol]:
          sale = transactions[o.symbol].pop(-1)
          if not sale.timestamp:
            print(sale)
          o.add_sale(sale.share_price - sale.fees, sale.timestamp)
        else:
          if not current_share_price:
            current_share_price = float(robin_stocks.stocks.get_latest_price(o.symbol)[0])
          o.add_sale(current_share_price, datetime.now(pytz.utc))
        for dividend in dividends:
          dividend_date = pytz.utc.localize(datetime.strptime(dividend['record_date'], '%Y-%m-%d'))
          if o.instrument_url == dividend['instrument'] and o.timestamp < dividend_date and (not sale or sale.timestamp > dividend_date):
            o.dividend_profit += float(dividend['rate'])

class Execution(object):
  def __init__(self, order, execution, symbol):
    self.order_id = order['id']
    self.instrument_url = order['instrument']
    self.symbol = symbol
    self.quantity = int(float(execution['quantity']))
    self.share_price = float(execution['price'])
    self.total_price = self.quantity * self.share_price
    self.fees = float(order['fees']) / float(order['quantity'])
    self.type = order['side'] # buy or sell
    self.timestamp = self._parse_datetime(execution['timestamp'])
    if self.type == 'sell':
      self.fees_computed = 0.00002 * self.total_price + 0.000119 * self.quantity + 0.02
      self.fees_computed = round(self.fees_computed, 2)
    self.profit = 0
    self.dividend_profit = 0
    self._sales = []

  def _parse_datetime(self, date_string):
    try:
      return pytz.utc.localize(datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ'))
    except ValueError:
      try:
        return pytz.utc.localize(datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ'))
      except ValueError:
        try:
          return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%f%z')
        except ValueError:
          return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S%z') 

  def add_sale(self, sale_amount, sale_timestamp):
    held_days = (sale_timestamp - self.timestamp).total_seconds() / 60  / 60 / 24
    self._sales.append([sale_amount, sale_timestamp, held_days])

  def average_days(self):
    if self.type == 'sell': return 0
    return int(sum(map(lambda x: x[2], self._sales)) / len(self._sales))

  def sale_profit(self):
    if self.type == 'sell': return 0
    return sum(map(lambda x: x[0], self._sales)) - self.total_price

  def total_profit_per_dollar(self):
    if self.type == 'sell': return 0
    return (self.sale_profit() + self.dividend_profit) / self.total_price

  def total_profit_per_dollar_per_day(self):
    if self.type == 'sell': return 0
    if self.average_days() < 1: return 0
    return self.total_profit_per_dollar() / self.average_days()

  def last_sale_date(self):
    if self.type == 'sell': return None
    return max(map(lambda x: x[1], self._sales))