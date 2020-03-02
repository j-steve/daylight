import copy
from datetime import datetime
import pytz

from entities.sale import Sale

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