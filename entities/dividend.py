from datetime import datetime
import pytz
import robin_stocks

class Dividend(object):
  def __init__(self, dividend_response):
    self.dividend_id = dividend_response['id']
    self.instrument_id = dividend_response['instrument']
    self.rate = float(dividend_response['rate'])
    self.quantity = float(dividend_response['position'])
    # TODO: The following localization assumes record_date is in UTC, which it is not.
    self.date = pytz.utc.localize(datetime.strptime(dividend_response['record_date'], '%Y-%m-%d'))

  @staticmethod
  def load_all():
    response = robin_stocks.helper.request_get(robin_stocks.urls.dividends(), 'pagination')
    return list(map(lambda d: Dividend(d), response))