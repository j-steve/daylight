from entities.execution import Execution

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
