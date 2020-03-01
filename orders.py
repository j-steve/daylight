from collections import defaultdict
import copy
from datetime import datetime
import pytz
import robin_stocks
import sqlite3
from entities.execution import Execution

def retrieve_all_orders():
  with sqlite3.connect('daylight.db') as db_conn:
    db_conn.row_factory = sqlite3.Row
    orders = list(_load_stock_orders(db_conn))
    orders.extend(_load_crypto_orders())
    orders.extend(_load_option_orders())
    orders.sort(key=lambda x: x.timestamp, reverse=True)
    buys = _associate_buys_and_sells(orders)
    return buys

def _load_stock_orders(db_conn):
  for order in robin_stocks.orders.get_all_orders():
    if order['state'] != 'filled':
      continue
    symbol = _load_instrument_symbol(db_conn, order['instrument'])
    for execution in order['executions']:
      yield Execution(
        'stock',
        execution,
        symbol=symbol,
        order_id=order['id'],
        buy_or_sell=order['side'],
        is_position_close=order['side'] == 'sell',
        instrument_id=order['instrument'],
        fees=float(order['fees']) / float(order['quantity']))

def _load_instrument_symbol(db_conn, instrument_id):
  cursor = db_conn.cursor()
  cursor.execute('CREATE TABLE IF NOT EXISTS Instruments(url TEXT PRIMARY KEY NOT NULL, symbol VARCHAR(5) NOT NULL)')
  cursor.execute('SELECT symbol FROM Instruments WHERE url = "{}"'.format(instrument_id))
  result = cursor.fetchall()
  if result:
    return result[0]['symbol']
  else:
    symbol = robin_stocks.helper.request_get(instrument_id)['symbol']
    cursor.execute('INSERT INTO Instruments VALUES("{}", "{}")'.format(instrument_id, symbol))
    return symbol

def _load_crypto_orders():
  currency_pairs = {}
  for pair in robin_stocks.crypto.get_crypto_currency_pairs():
    currency_pairs[pair['id']] = pair['asset_currency']['code']
  crypto_orders = robin_stocks.helper.request_get(robin_stocks.urls.order_crypto(), 'pagination')
  for order in crypto_orders:
    if order['state'] != 'filled':
      continue
    currency_pair_id = order['currency_pair_id']
    for execution in order['executions']:
      execution['price'] = execution['effective_price']
      yield Execution(
        'crypto',
        execution, 
        symbol=currency_pairs[currency_pair_id], 
        order_id=order['id'],
        buy_or_sell=order['side'],
        is_position_close=order['side'] == 'sell')

def _load_option_orders():
  for option in robin_stocks.options.get_market_options():
    if option['state'] != 'filled':
      continue
    for leg in option['legs']:
      for execution in leg['executions']:
        if False:
          yield Execution(
            'option',
            execution,
            symbol=option['chain_symbol'],
            order_id=option['id'],
            buy_or_sell=leg['side'],
            is_position_close=leg['position_effect'] == 'close')

def _associate_buys_and_sells(orders):
  dividends = Dividend.load_all()
  sales = defaultdict(lambda: [])
  for execution in orders:
    print(execution.symbol, execution.buy_or_sell, execution.quantity)
    symbol_sales = sales[execution.symbol]
    if execution.is_position_close:
      symbol_sales.append(Sale(execution))
    else:
      buy = Buy(execution)
      symbol_sales = sales[buy.execution.symbol]
      while buy.unsold_quantity and symbol_sales:
        sale = symbol_sales.pop(-1)
        remaining_sale_portion = buy.add_sale(sale)
        if remaining_sale_portion: symbol_sales.append(remaining_sale_portion)
      if buy.unsold_quantity:
        if execution.instrument_type == 'stock':
          buy.market_price = float(robin_stocks.stocks.get_latest_price(execution.symbol)[0])
        else:
          buy.market_price = float(robin_stocks.crypto.get_crypto_quote(execution.symbol)['mark_price'])
      if execution.instrument_type == 'stock':
        for dividend in dividends:
          buy.try_add_dividend(dividend)
      yield buy

class Dividend(object):
  def __init__(self, dividend_response):
    self.dividend_id = dividend_response['id']
    self.instrument_id = dividend_response['instrument']
    self.rate = float(dividend_response['rate'])
    self.quantity = float(dividend_response['position'])
    self.date = pytz.utc.localize(datetime.strptime(dividend_response['record_date'], '%Y-%m-%d'))

  @staticmethod
  def load_all():
    response = robin_stocks.helper.request_get(robin_stocks.urls.dividends(), 'pagination')
    return list(map(lambda d: Dividend(d), response))

class Sale(object):
  def __init__(self, parent, quantity=None):
    """
    Args:
      parent (Sale, Execution): The original/parent entity.
      quantity (float): The quantity for this Sale.  If not provided, defaults to parent.quantity.
    """
    assert isinstance(parent, (Sale, Execution)) 
    self.order_id = parent.order_id
    self.quantity = parent.quantity if quantity is None else quantity
    portion_of_parent = self.quantity / parent.quantity
    self.fees = parent.fees * portion_of_parent
    self.total_price = parent.total_price * portion_of_parent
    self.timestamp = parent.timestamp


class Buy(object):
  def __init__(self, execution):
    self.execution = execution
    self.unsold_quantity = self.execution.quantity
    self.market_price = 0
    self._dividends = []
    self._sales = []

  def add_sale(self, sale):
    """
    Associates a new Sale with this Buy.
    If the quantity sold exceeds the remaining unsold quantity for this Buy,
    returns a new Sale object representing the excess.
    """
    buy_sold_quantity = min(sale.quantity, self.unsold_quantity)
    self._sales.append(Sale(sale, buy_sold_quantity))
    self.unsold_quantity -= buy_sold_quantity
    remaining_sale_quantity =  sale.quantity - buy_sold_quantity
    if remaining_sale_quantity > 0:
      return Sale(sale, remaining_sale_quantity)

  def try_add_dividend(self, dividend):
    """
    Evaluates whether the given dividend is applicable for this Buy.
    If so, adds a copy of the dividend, and subtracts the used quantity from the given dividend.
    """
    if dividend.quantity and self.execution.instrument_id == dividend.instrument_id and self.execution.timestamp < dividend.date:
      prior_sales = filter(lambda s: s.timestamp < dividend.date, self._sales)
      buy_dividend_qty = self.execution.quantity - sum(map(lambda s: s.quantity, prior_sales))
      if buy_dividend_qty:  # Entire position was not [yet] sold prior to this dividend.
        dividend_to_add = copy.copy(dividend)
        dividend_to_add.quantity = min(buy_dividend_qty, dividend.quantity)
        self._dividends.append(dividend_to_add)
        dividend.quantity -= dividend_to_add.quantity

  def sale_fees(self):
    return sum(map(lambda s: s.fees, self._sales))

  def sale_profit(self):
    return sum(map(lambda s: s.total_price, self._sales)) + self.unsold_quantity * self.market_price - self.execution.total_price
  
  def dividend_earnings(self):
    return sum(map(lambda d: d.rate * d.quantity, self._dividends))

  def total_profit(self):
    return self.sale_profit() + self.dividend_earnings()

  def total_profit_per_dollar(self):
    return self.total_profit() / self.execution.total_price
    
  def total_profit_per_dollar_per_day(self):
    return self.total_profit() / self.execution.total_price / self.average_days()

  def average_days(self):
    sold_total_secs = sum(map(lambda s: (s.timestamp - self.execution.timestamp).total_seconds() * (s.quantity / self.execution.quantity), self._sales))
    unsold_secs = (datetime.now(pytz.utc) - self.execution.timestamp).total_seconds() * (self.unsold_quantity / self.execution.quantity)
    return (sold_total_secs + unsold_secs) / 60 / 60 / 24
  
  def last_sale_date(self):
    return max(map(lambda s: s.timestamp, self._sales)) if not self.unsold_quantity else None

  # def unsold_quantity(self):
  #   """Returns the quantity purchased which has not (yet) been subsequently sold, if any."""
  #   return self.execution.quantity - sum(map(lambda s: s.quantity, self.sales))