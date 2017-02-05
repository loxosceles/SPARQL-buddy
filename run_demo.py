#!/usr/bin/env python

q = """\"\"\"dbo dbp dbr
SELECT ?population ?populated_place
  WHERE {
    ?populated_place a dbo:PopulatedPlace .
    ?populated_place dbo:country dbr:Russia .
    ?populated_place dbp:population ?population .
    MINUS {dbr:MacKlintok_Island dbp:population ?population}
  }\"\"\"  """

command_list = ['sq.run_query(%(query)s)' % {'query':q}, 'sq.print_latest_query()']

def run():
    for i in command_list:
        print(i)
        exec(i)
