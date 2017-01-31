#!/usr/bin/env python

import rdflib, json, csv, sys, traceback, fnmatch
from SPARQLWrapper import SPARQLWrapper, JSON
from os import walk, listdir
import itertools
import os, signal, time
import threading
#from pudb import set_trace; set_trace()

default_url = "http://dbpedia.org/sparql"
default_prefix_file = "./prefixes.csv"
default_query_path = "./queries/"


class SQObject:
    def __init__(self):
        self.id = id(self) 
        self.query = "" 
        self.response = dict()
        self.keyword = ""
        self.s_type = ""

    @property
    def query(self): 
        return self._query

    @query.setter
    def query(self, value):
        self._query = value

    @property
    def response(self): 
        return self._response

    @response.setter
    def response(self, value):
        self._response = value

    @property
    def keyword(self):
        return self._keyword

    @keyword.setter
    def keyword(self, value):
        self._keyword = value

    @property
    def s_type(self):
        return self._s_type

    @s_type.setter
    def s_type(self, value):
        self._s_type = value

    def print_query(self):
        print("\n" + self._query)

    def print_response(self):
        print(json.dumps(self._response, indent=4, sort_keys=True))

    def print_raw_response(self):
        print(self._response)

    def filter_types(self):
        for i in self.response['results']['bindings']:
            print(i['type']['value'])

    def filter_attributes(self):
        for i in self._response['results']['bindings']:
            for j in i:
                print(j + ": " + i[j]['value'])
            print()


class SQuery:
    """
    Objects of this class comprise a particular query environment, so that every
    instance will query with different query parameters:
        * url of SPARQL endpoint
        * prefix file where prefix abreviations are defined, can be used to group
          prefixes since not every query needs all of them
        * query path, path where queries can be stored
    If no parameters are given when instantiated, default values will be used.
    """
    
    def __init__(self, url=default_url, prefixes=default_prefix_file, dqp=default_query_path):
        self.url = url
        self.prefix_file = prefixes
        self.dqp = dqp                              # default query path
        self.g = SPARQLWrapper(self.url)
        self.prefixes_dict = dict() 
        self.generate_prefix_dict(self.prefix_file)
        self.query_list = []                        # list of recent query objects
        #self.latest_qobj = self.latest_qobj() 

    def run_query(self, inpt, fmt=""):
        """
        runs a query
        params: inpt, can be file or string
                r, 'r' prints raw JSON format
        """
        obj = SQObject()
        obj.query = self.compose_query(inpt)
        self.g.setReturnFormat(JSON)
        self.g.setQuery(obj.query)
        obj.response = self.g.query().convert()
        self.query_list.append(obj)

        if fmt is not 'boolean':
            if fmt is "raw":
                obj.print_raw_response()
            elif fmt is "f":
                print("debugging")
                obj.filter_attributes()
            else:
                obj.print_response()

    def compose_query(self, q):
        prefix_list = []
        prefix_string = ""
        query = ""

        try:
            prefix_list = q.split("\n", 1)[0].split()
            query = q.split("\n", 1)[1] 
        except (IndexError, AttributeError) as e:
            try:
                if type(q) is int: q = list_queries()[q]

                q_relpath = self.dqp + q

                with open(q_relpath) as f:
                    prefix_list = f.readline().strip().split()
                    query = f.read()
            except FileNotFoundError:
                    sys.exit('File name wrong?')

        for item in prefix_list:
            prefix_string = prefix_string + self.concat_prefix_string(item) + "\n"
        return prefix_string + query

    def handler(self, signum, frame):
        raise Exception("Query timed out!")

#    def status_bar(self,wt):
#        
#        clear = lambda: os.system('clear')
#        clear() 
#
#        for i in range(wt + 1):
#            print('|' + ((i + 1) * '#') + (((wt - 1) - i) * ' ') + '|')
#            time.sleep(1)
#            clear() 
#        else:
#            print()


    def keyword_search(self, kw, mode='extended'):

        sparql_q = """foaf rdf rdfs schema
                   SELECT ?place ?person ?action ?organization ?event ?name
                   WHERE { 
                           { 
                           ?place rdf:type schema:Place ;
                           rdfs:label ?name
                           } UNION {
                           ?person rdf:type schema:Person ;
                           rdfs:label ?name
                           } UNION {
                           ?action rdf:type schema:Action ;
                           rdfs:label ?name
                           } UNION {
                           ?organization rdf:type schema:Organization ;
                           rdfs:label ?name
                           } UNION {
                           ?event rdf:type schema:Event ;
                           rdfs:label ?name
                           }
                       FILTER (lang(?name) = "en")
                       FILTER REGEX(?name, %(regex)s) .
                   }
                """ 

        quick = """dbr rdf rdfs 
                    ASK {
                    dbr:%(keyword)s ?p ?o .   
                }
                """ % {'keyword':kw.title().replace(" ", "_")}

        wait_time = 60
        signal.signal(signal.SIGALRM, self.handler)

        signal.alarm(wait_time)
        #bar = threading.Thread(target=self.status_bar(wait_time))
        #bar.start()
        try:
            if mode == 'strict':
                print('*---------------*')
                print('| Strict Search |')
                print('*---------------*')

                regex = "'^%(kw)s$', 'i'" % {'kw':kw}
                q = sparql_q % {'regex':regex}
                self.run_query(q)
            elif mode == 'extended':
                print('*-----------------*')
                print('| Extended Search |')
                print('*-----------------*')

                regex = "'^([A-z]+ )*%(kw)s,?( [A-z]+)*$', 'i'" % {'kw':kw} 
                q = sparql_q % {'regex':regex}
                self.run_query(q)
            elif mode == 'quick':
                print('*--------------*')
                print('| Quick Search |')
                print('*--------------*')

                self.run_query(quick, 'boolean')

                if bool(self.query_list[-1].response['boolean']) is True:
                    print("<http://dbpedia.org/resource/%(kw)s>" % {'kw':kw.title().replace(" ", "_")})
                else:
                    print("Not found")

                del self.query_list[-1]
                
            print('\n')
        except Exception as e:
            print(e)
        signal.alarm(0)
                

    def clear_query_list(self):
        self.query_list.clear()

    def print_query_list(self):
        for o in self.query_list:
            print(o)

    def generate_prefix_dict(self, pf):
        with open(pf, mode='r') as infile:
            tmp = csv.reader(infile)
            try:
                self.prefixes_dict = {rows[0]:rows[1] for rows in tmp}
            except IndexError as e:
                sys.exit("Prefixes file should not contain blank lines")
    
    def latest_qobj(self):
        if self.query_list:
            return self.query_list[-1] 

    def print_latest_query(self):
        tmp = self.latest_qobj().print_query()

    def print_latest_response(self):
        self.latest_qobj().print_response()

    def set_url(self, url):
        self.url = url
        self.g = SPARQLWrapper(self.url)

    def concat_prefix_string(self, prefix):
        return "PREFIX " + prefix + ": " + self.prefixes_dict[prefix] + " "

    def print_prefixes():
        """
        TODO
        """
        pass


def list_queries(path=default_query_path):
    return dict(enumerate([f for f in listdir(path) 
        if not fnmatch.filter(f, '.*')]))

sq = SQuery()
