#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#	SNOMED import utilities, extracted from umls.py
#
#	2014-01-20	Created by Pascal Pfiffner
#

import sys
import os
import csv
import logging

from sqlite import SQLite


class SNOMED (object):
	sqlite_handle = None
	
	@classmethod
	def import_from_files_if_needed(cls, rx_map):
		for table, filepath in rx_map.items():
			num_query = 'SELECT COUNT(*) FROM {}'.format(table)
			num_existing = cls.sqlite_handle.executeOne(num_query, ())[0]
			if num_existing > 0:
				continue
			
			cls.import_csv_into_table(filepath, table)
	
	
	@classmethod
	def import_csv_into_table(cls, snomed_file, table_name):
		""" Import SNOMED CSV into our SQLite database.
		The SNOMED CSV files can be parsed by Python's CSV parser with the
		"excel-tab" flavor.
		"""
		
		logging.debug('..>  Importing SNOMED {} into snomed.db...'.format(table_name))
		
		# not yet imported, parse tab-separated file and import
		with open(snomed_file, encoding='utf-8') as csv_handle:
			cls.sqlite_handle.isolation_level = 'EXCLUSIVE'
			sql = cls.insert_query_for(table_name)
			reader = csv.reader(csv_handle, dialect='excel-tab')
			i = 0
			try:
				for row in reader:
					if i > 0:			# first row is the header row
						
						# execute SQL (we just ignore duplicates)
						params = cls.insert_tuple_from_csv_row_for(table_name, row)
						try:
							cls.sqlite_handle.execute(sql, params)
						except Exception as e:
							sys.exit('Cannot insert {}: {}'.format(params, e))
					i += 1
				
				# commit to file
				cls.sqlite_handle.commit()
				cls.did_import(table_name)
				cls.sqlite_handle.isolation_level = None
			
			except csv.Error as e:
				sys.exit('CSV error on line {}: {}'.format(reader.line_num, e))

		logging.debug('..>  {} concepts parsed'.format(i-1))


	@classmethod
	def setup_tables(cls):
		""" Creates the SQLite tables we need, not the tables we deserve.
		Does nothing if the tables/indexes already exist
		"""
		if cls.sqlite_handle is None:
			cls.sqlite_handle = SQLite.get(os.path.join('databases', 'snomed.db'))
		
		# descriptions
		cls.sqlite_handle.create('descriptions', '''(
				concept_id INTEGER PRIMARY KEY,
				lang TEXT,
				term TEXT,
				isa VARCHAR,
				active INT
			)''')
		cls.sqlite_handle.execute("CREATE INDEX IF NOT EXISTS isa_index ON descriptions (isa)")
		
		# relationships
		cls.sqlite_handle.create('relationships', '''(
				relationship_id INTEGER PRIMARY KEY,
				source_id INT,
				destination_id INT,
				rel_type INT,
				rel_text VARCHAR,
				active INT
			)''')
		cls.sqlite_handle.execute("CREATE INDEX IF NOT EXISTS source_index ON relationships (source_id)")
		cls.sqlite_handle.execute("CREATE INDEX IF NOT EXISTS destination_index ON relationships (destination_id)")
		cls.sqlite_handle.execute("CREATE INDEX IF NOT EXISTS rel_type_index ON relationships (rel_type)")
		cls.sqlite_handle.execute("CREATE INDEX IF NOT EXISTS rel_text_index ON relationships (rel_text)")
		
	
	@classmethod
	def insert_query_for(cls, table_name):
		""" Returns the insert query needed for the given table
		"""
		if 'descriptions' == table_name:
			return '''INSERT OR IGNORE INTO descriptions
						(concept_id, lang, term, isa, active)
						VALUES
						(?, ?, ?, ?, ?)'''
		if 'relationships' == table_name:
			return '''INSERT OR IGNORE INTO relationships
						(relationship_id, source_id, destination_id, rel_type, active)
						VALUES
						(?, ?, ?, ?, ?)'''
		return None
	
	
	@classmethod
	def insert_tuple_from_csv_row_for(cls, table_name, row):
		if 'descriptions' == table_name:
			isa = ''
			if len(row) > 6:
				if '900000000000013009' == row[6]:
					isa = 'synonym'
				elif '900000000000003001' == row[6]:
					isa = 'full'
			return (int(row[4]), row[5], row[7], isa, int(row[2]))
		if 'relationships' == table_name:
			return (int(row[0]), int(row[4]), int(row[5]), int(row[7]), int(row[2]))
		return None
	
	
	@classmethod
	def did_import(cls, table_name):
		""" Allows us to set hooks after tables have been imported
		"""
		if 'relationships' == table_name:
			cls.sqlite_handle.execute('''
				UPDATE relationships SET rel_text = 'isa' WHERE rel_type = 116680003
			''')
			cls.sqlite_handle.execute('''
				UPDATE relationships SET rel_text = 'finding_site' WHERE rel_type = 363698007
			''')


# running this script with a path argument starts the data import
if '__main__' == __name__:
	logging.basicConfig(level=logging.DEBUG)
	
	if len(sys.argv) < 2:
		print("""Provide the path to the extracted SNOMED directory as first argument.
			\nDownload SNOMED from http://www.nlm.nih.gov/research/umls/licensedcontent/snomedctfiles.html""")
		sys.exit(0)
	
	# find file function
	def _find_files(directory, prefix):
		for root, dirs, files in os.walk(directory):
			for name in files:
				if name.startswith(prefix):
					return os.path.join(directory, name)
			
			for name in dirs:
				found = _find_files(os.path.join(directory, name), prefix)
				if found:
					return found
		return None
	
	# table to file mapping
	prefixes = {
		'descriptions': 'sct2_Description_Full-en_INT_',
		'relationships': 'sct2_Relationship_Full_INT_'
	}
	found = {}
	snomed_dir = sys.argv[1]
	
	# try to find the files
	for table, prefix in prefixes.items():
		found_file = _find_files(snomed_dir, prefix)
		if found_file is None:
			raise Exception('Unable to locate file starting with "{}" in SNOMED directory at {}'.format(prefix, snomed_dir))
		found[table] = found_file
	
	# import from files
	try:
		SNOMED.sqlite_handle = None
		SNOMED.setup_tables()
		SNOMED.import_from_files_if_needed(found)
	except Exception as e:
		raise Exception("SNOMED import failed: {}".format(e))
