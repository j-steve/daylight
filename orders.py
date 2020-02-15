import robin_stocks
from decimal import Decimal

def parse(orders):
  for order in orders:
    instrument = robin_stocks.helper.request_get(order['instrument'])
    yield Order(order, instrument)

class Order(object):
  def __init__(self, order, instrument):
    self.id = order['id']
    self.symbol = instrument['symbol']
    self.quantity = float(order['cumulative_quantity'] or 0)
    if order['executed_notional']:
      self.total_price = float(order['executed_notional']['amount'] or 0)
    else:
      self.total_price = 0
    self.share_price = self.total_price / self.quantity if self.quantity else None
    self.fees = float(order['fees'] or 0)
    self.type = order['side'] # buy or sell
    self.timestamp = order['executions'] and order['executions'][0]['timestamp'] or None
    if self.type == 'sell':
      self.fees_computed = 0.00002 * self.total_price + 0.000119 * self.quantity + 0.02
      self.fees_computed = round(self.fees_computed, 2)
