import robin_stocks
from decimal import Decimal

def parse(orders):
  for order in orders:
    if order['state'] != 'filled':
      continue
    instrument = robin_stocks.helper.request_get(order['instrument'])
    for execution in order['executions']:
      yield Order(order, execution, instrument)

class Order(object):
  def __init__(self, order, execution, instrument):
    self.id = order['id']
    self.symbol = instrument['symbol']
    self.quantity = float(execution['quantity'])
    self.share_price = float(execution['price'])
    self.total_price = self.quantity * self.share_price
    self.fees = float(order['fees'] or 0)
    self.type = order['side'] # buy or sell
    self.timestamp = execution['timestamp'] or None
    if self.type == 'sell':
      self.fees_computed = 0.00002 * self.total_price + 0.000119 * self.quantity + 0.02
      self.fees_computed = round(self.fees_computed, 2)
