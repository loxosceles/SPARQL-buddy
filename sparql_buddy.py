#!/usr/bin/env python

import rdflib, json, csv, sys, traceback, fnmatch
from SPARQLWrapper import SPARQLWrapper, JSON
from os import walk, listdir
import itertools
import os, signal, time
import threading

default_url = "http://dbpedia.org/sparql"
default_prefix_file = "./prefixes.csv"
default_query_path = "./queries/"


class SQObject:
    """
    Objects of this class hold a single query and all its 
    associated information, like id, name, rquery (not 
    abbreviated), query, response, type, etc.
    """
    def __init__(self):
        self.id = id(self) 
        self.name = ""
        self.query = "" 
        self.rquery = "" 
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
    def rquery(self): 
        return self._rquery

    @rquery.setter
    def rquery(self, value):
        self._rquery = value

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
            for j in i:
                print(j + ": " + i[j]['type'])
            print()

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
    
    def __init__(self, url=default_url, 
                 prefixes=default_prefix_file,
                 query_file_folder=default_query_path):
        self.url = url
        self.prefix_file = prefixes
        self.query_file_folder = query_file_folder                              # default query path
        self.g = SPARQLWrapper(self.url)
        self.prefix_mapping_dict = self.prefix_mapping() 
        self.query_files_dict = self.query_files
        self.track_list = []                        # list of recent query objects

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        self._url = url
        self.g = SPARQLWrapper(self._url)

    @property
    def prefix_file(self):
        return self._prefix_file

    @prefix_file.setter
    def prefix_file(self, path):
        self._prefix_file = path

    @property
    def query_files(self): 
        self.query_files_dict = dict(enumerate(
        [f for f in listdir(self.query_file_folder) 
        if not fnmatch.filter(f, '.*')]))
        return self.query_files_dict

    def run_query(self, inpt, fmt=""):
        """
        runs a query
        params: inpt, can be file or string
                r, 'r' prints raw JSON format
        """
        obj = SQObject()
        obj.query, obj.rquery = self.compose_query(inpt)
        self.g.setReturnFormat(JSON)
        self.g.setQuery(obj.query)
        obj._response = self.g.query().convert()
        self.track_list.append(obj)

        if fmt is not 'boolean':
            if fmt is "raw":
                obj.print_raw_response()
            else:
                obj.print_response()

    def compose_query(self, q):
        prefix_list = []
        prefix_string = ""
        query = ""

        try:
            # Assuming it is a immediate query:
            # make list out of prefix abreviations
            prefix_list = q.split("\n", 1)[0].split()
            # assign pure query to variable
            query = q.split("\n", 1)[1] 
        except (IndexError, AttributeError) as e:
        # found out it was a index number and has to be read from file
            try:
                # if it is a number, so take name from query list
                if type(q) is int:
                    q = self.query_files_dict[q]
                    print("Issuing " + q)

                # prepend the relative path to query
                q_relpath = self.query_file_folder + q

                with open(q_relpath) as f:
                    prefix_list = f.readline().strip().split()
                    query = f.read()
            except FileNotFoundError:
                # not a file, a number or a query name
                sys.exit('File name wrong?')

        # save the query with abreviated prefixes
        for item in prefix_list:
            prefix_string = prefix_string + self.concat_prefix_string(item) + "\n"
        # return query twice: first with replaced prefixes, second without
        return (prefix_string + query, ' '.join(prefix_list) + '\n' + query)

    def handler(self, signum, frame):
        raise Exception("Query timed out!")

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

                keyword = kw.title().replace(" ", "_")
                q = quick % {'keyword':keyword}
                self.run_query(q, 'boolean')

                if bool(self.track_list[-1].response['boolean']) is True:
                    #FIXME: hardcoded db-endpoint
                    print("<http://dbpedia.org/resource/%(kw)s>" % {'kw':keyword})
                else:
                    print("Not found")

                del self.track_list[-1]
                
            print('\n')
        except Exception as e:
            print(e)
        signal.alarm(0)
    
    def query2file(self, query, filename):
        with open(self.query_file_folder + filename, "w") as text_file:
            text_file.write(query)

    def clear_track_list(self):
        self.track_list.clear()

    def print_track_list(self):
        print('\n')
        for o in self.track_list:
            print('id: ' + str(o.id))

    def prefix_mapping(self):
        with open(self.prefix_file, mode='r') as infile:
            tmp = csv.reader(infile)
            try:
                return {rows[0]:rows[1] for rows in tmp}
            except IndexError as e:
                sys.exit("Prefixes file should not contain blank lines")
    
    def latest_qobj(self, offset=1):
        try:
            return self.track_list[-int(offset)] 
        except IndexError: 
            print("No queries have been issued") 

    def print_latest_query(self):
        try:
            print(self.latest_qobj()._query)
        except AttributeError:
            print("Query list empty")

    def print_latest_response(self):
        self.latest_qobj().print_response()

    def concat_prefix_string(self, prefix):
        try:
            return "PREFIX " + prefix + ": " + self.prefix_mapping_dict[prefix] + " "
        except:
            print('Prefix not defined')
            self.prefix_mapping_dict = self.prefix_mapping()
            return "PREFIX " + prefix + ": " + self.prefix_mapping_dict[prefix] + " "

    def print_prefixes(self):
        """
        Shows a list of prefixes and associated namespaces
        """
        self.prefix_mapping_dict = self.prefix_mapping()
        for k, v in self.prefix_mapping_dict.items():
            print('\t' + k + ':\t ' + v)

def list_qfiles(*objs):

    for i in objs:
        print('\n' + i.url + '\n')
        # making sure that the mappings will be written to a dict
        i.query_files_dict = i.query_files
        for k, v in i.query_files_dict.items():
            print('\t' + str(k) + ':\t' + v)

sq = SQuery()
