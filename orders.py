import robin_stocks
from collections import defaultdict
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
  orders.sort(key=lambda x: x.timestamp)
  transactions = defaultdict(lambda: [])
  for o in orders:
    if o.type == 'buy':
      for i in range(o.quantity):
        transactions[o.symbol].append(o.share_price)
    elif o.type == 'sell':
      o.profit = o.total_price - o.fees
      for i in range(o.quantity):
        if transactions[o.symbol]:
          # May be no buy transaction, if this was 
          # a free robinhood stock.
          o.profit -= transactions[o.symbol].pop(-1)
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
    self.symbol = instrument['symbol']
    self.quantity = int(float(execution['quantity']))
    self.share_price = float(execution['price'])
    self.total_price = self.quantity * self.share_price
    self.fees = float(order['fees']) / int(float(order['quantity']))
    self.type = order['side'] # buy or sell
    self.timestamp = execution['timestamp'] or None
    if self.type == 'sell':
      self.fees_computed = 0.00002 * self.total_price + 0.000119 * self.quantity + 0.02
      self.fees_computed = round(self.fees_computed, 2)
    self.profit = None
