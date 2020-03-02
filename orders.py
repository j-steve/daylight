from collections import defaultdict
import robin_stocks
import sqlite3

from entities.execution import Execution
from entities.buy import Buy
from entities.dividend import Dividend
from entities.sale import Sale

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
        is_position_close=order['side'] == 'sell',
        instrument_id=currency_pair_id)

def _load_option_orders():
  for option in robin_stocks.options.get_market_options():
    if option['state'] != 'filled':
      continue
    for leg in option['legs']:
      for execution in leg['executions']:
        execution['quantity'] = float(execution['quantity']) * 100
        if (leg['side'] == 'sell') != (leg['position_effect'] == 'close'): 
          execution['price'] = 0 - float(execution['price'])
        yield Execution(
          option['opening_strategy'],
          execution,
          symbol=option['chain_symbol'],
          order_id=option['id'],
          buy_or_sell=leg['side'],
          is_position_close=leg['position_effect'] == 'close',
          instrument_id=leg['option'])

def _associate_buys_and_sells(orders):
  dividends = Dividend.load_all()
  sales = defaultdict(lambda: [])
  for execution in orders:
    print(execution.symbol, execution.buy_or_sell, execution.quantity)
    symbol_sales = sales[execution.instrument_id]
    if execution.is_position_close:
      symbol_sales.append(Sale(execution))
    else:
      buy = Buy(execution)
      symbol_sales = sales[buy.execution.instrument_id]
      while buy.unsold_quantity and symbol_sales:
        sale = symbol_sales.pop(-1)
        remaining_sale_portion = buy.add_position_close(sale)
        if remaining_sale_portion: symbol_sales.append(remaining_sale_portion)
      if buy.unsold_quantity:
        if execution.instrument_type == 'stock':
          buy.market_price = float(robin_stocks.stocks.get_latest_price(execution.symbol)[0])
        elif execution.instrument_type == 'crypto':
          buy.market_price = float(robin_stocks.crypto.get_crypto_quote(execution.symbol)['mark_price'])
        else:
          option_id = robin_stocks.helper.request_get(execution.instrument_id)['id']
          market_data = robin_stocks.options.get_option_market_data_by_id(option_id)
          buy.market_price = float(market_data['adjusted_mark_price'])
      if execution.instrument_type == 'stock':
        for dividend in dividends:
          buy.try_add_dividend(dividend)
      yield buy