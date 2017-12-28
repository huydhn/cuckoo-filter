'''
Cuckoo filter internal exception.
'''

class CapacityException(Exception):
    '''
    Raise when a filter reaches its capacity.
    '''
    pass


class InconsistencyException(Exception):
    '''
    Raise when a filter becomes inconsistent.  All bets are off.
    '''
    pass
