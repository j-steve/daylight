import robin_stocks

def parse(orders):
  for o in orders:
    yield _parse_order(o)

def _parse_order(order):
  instrument = robin_stocks.helper.request_get(order['instrument'])
  order['symbol'] = instrument['symbol']
  return order