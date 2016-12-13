#!/usr/bin/env python

"""First argument is endpoint if it looks like a URL, remaining args
are names of files with SPARQL queries. Sends query in file F to the
endpoint and writes response to file F.out. Example:
  python sparql.py http://dbpedia.org/sparql myquery.txt
"""

import sys, urllib, json

usage = """USAGE: python sparql.py [endpoint] q1file q2file ... qnfile"""

default_endpoint = "http://dbpedia.org/sparql"
default_format = "application/json"

def ask_query(query, endpoint=default_endpoint, format=default_format):
    params={"query":query,
            "format":format,            
            "default-graph":"",     
            "debug":"on",
            "timeout":"",
            "save":"display",
            "fname":"" }
    try:
        response = urllib.urlopen(endpoint, urllib.urlencode(params)).read()
        return json.loads(response)        
    except:
        return None

def json2html(data):
    """ Constructs an HTML table string from a json object resulting from a sparql query"""
    html = '<table border="1">'
    if 'head' in data:
        # the json is from a select sparql query
        vars = data['head']['vars']
        html = '<table  border="1"><thead><tr>' + ''.join(['<th> %s </th>' % var for var in vars]) + '</tr></thead><tbody>'
        for result in data['results']['bindings']:
            html += '<tr>' + ''.join(['<td>%s</td>' % (linkify(result.get(var,{}).get('value', '')),) for var in vars]) + '</tr>'
        html += '</tr></tbody>'
    else:
        # the json is from a construct sparql query
        for (s, po) in data.items():
            for (p, objs) in po.items():
                for o in objs:
                    html += '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (linkify(s), linkify(p), linkify(o['value']))

    return html + '</table>'

def linkify(string):
    """ if string looks like a URI, turn it into a link """
    return '<a href="%s">%s</a>' % (string, string) if string.startswith('http://') else string

        
def output(file, endpoint):
    print('query', file)
    data = ask_query(open(file).read(), endpoint)
    if data:
        out_html = open(file+".html", 'w')
        #out_json = open(file+".json", 'w')    
        #out_json.write(json.dumps(data))
        out_html.write("<html><body>"+json2html(data)+"</body></html>")
        #print(json2html(data))
        out_html.close()
        #out_json.close()
    else:
        print('query failed')
        

def main():
    """If run as a script, invoke this"""
    if len(sys.argv) < 2:
        sys.exit(usage)
    elif sys.argv[1].lower().startswith('http'):
        endpoint = sys.argv[1]
        files = sys.argv[2:]
    else:
        endpoint = default_endpoint
        files = sys.argv[1:]
    for file in files:
        output(file, endpoint)
        
if __name__ == "__main__":
    main()
