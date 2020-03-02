from datetime import datetime
import pytz

class Execution(object):
  def __init__(self, instrument_type, execution, symbol, order_id, buy_or_sell, is_position_close, instrument_id, fees=0):
    self.instrument_type = instrument_type
    self.timestamp = self._parse_datetime(execution['timestamp'])
    self.quantity = float(execution['quantity'])
    self.share_price = float(execution['price'])
    self.total_price = self.quantity * self.share_price
    self.order_id = order_id
    self.symbol = symbol
    self.buy_or_sell = buy_or_sell
    self.is_position_close = is_position_close
    self.fees = fees
    self.instrument_id = instrument_id
    # if self.type == 'sell':
    #   self.fees_computed = 0.00002 * self.total_price + 0.000119 * self.quantity + 0.02
    #   self.fees_computed = round(self.fees_computed, 2)

  @staticmethod
  def _parse_datetime(date_string):
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