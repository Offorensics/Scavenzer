#!/usr/bin/env python3

import os
import sys
import re
import textract
import tarfile
import platform
import argparse
import shutil
import zipfile
from termcolor import colored
from random import randint

class SearchPattern():

	def __init__(self):

		# Possible search objects
		self.search_objects = ["phone", "email"]
		self.regex_patterns = {
					"phone": {
						"US": r"((?:\+1\.)?\(?[0-9]{3}\)?[ \.-][2-9][0-9]{2}[ \.-][0-9]{4})",
						"FI": r"((?:\+358|0)[4-5][05][ ]?[0-9]{3}[ ]?[0-9]{4})",
						"SWE": r"((?:\+46|0)(?:10|7[02369])[ ]?[0-9]{4}[ ]?[0-9]{3})"
						},
					"email": {"General": r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"
						}
				}

		self.exceptions = (
				textract.exceptions.ExtensionNotSupported,
				textract.exceptions.MissingFileError,
				UnicodeDecodeError,
				textract.exceptions.ShellError,
				MemoryError,
				KeyError,
				RuntimeError,
				zipfile.BadZipFile,
				FileNotFoundError,
				tarfile.ReadError
				)

		# Get operating system name
		self.os_platform = platform.system()

		if self.os_platform == "Linux":
			self.home_dir = os.path.expanduser("~") + "/"
		elif self.os_platform == "Windows":
			self.home_dir = os.path.expanduser("~") + "\\"

		self.temp_dir_base = self.home_dir + "scavenzer_"

		# Get user's search object and directory, defaults to 'email' and 'pwd'
		self.search_obj, self.base_dir, self.domain, self.ccodes, self.outp = self.get_params()

		if self.domain != None:
			self.regex_patterns['email'] = {"User Domain":  r"([a-zA-Z0-9_.+-]+@" + self.domain[0] + ")"}

		# Under given directory, list all files and return them in a list
		self.file_list = self.find_files(self.base_dir)

		self.regex_dic = self.regex_patterns[self.search_obj]

		if self.search_obj == "phone" and "all" not in self.ccodes:
			for ccode in list(self.regex_dic.keys()):
				if ccode not in self.ccodes:
					del self.regex_dic[ccode]

		self.find_pattern()

	# Get and validate parameters given by user
	def get_params(self):

		# List possible arguments
		parser = argparse.ArgumentParser()
		parser.add_argument("-b", metavar="[BASE DIRECTORY]", nargs=1, help="Base directory")
		parser.add_argument("-o", action="store_true", help="Show only matched patterns")
		parser.add_argument("--search", metavar="[SEARCH OBJECT]", nargs=1, help="Possible values: email (default), phone")
		parser.add_argument("--domain", metavar="[DOMAIN NAME]", nargs=1, help="Specific domain name (e.g. gmail.com). Works only with email search")
		parser.add_argument("--country-code", metavar="[COUNTRY CODES]", nargs='+', help="Limit phone search to specific countries. If not used, default is US. 'all' can be used as well.")

		# Get arguments
		args = parser.parse_args()
		base_dir = args.b
		outp = args.o
		search_obj = args.search
		domain = args.domain
		ccodes = args.country_code

		# Check if optional -d argument is used
		if base_dir != None:
			base_dir = base_dir[0]

			# If -d argument has value, check if the directory exists on the system
			if not os.path.exists(base_dir):
				print("Given path '" + base_dir + "' doesn't exist")
				sys.exit()

		# If -d argument is not being used, use default value
		else:
			base_dir = os.getcwd()

		# Check if optional --search argument is used
		if search_obj != None:
			search_obj = search_obj[0]

			# Check if it is a valid search object
			if search_obj not in self.search_objects:
				print("Search object ' " + str(search_obj) + "' cannot be recognized")
				sys.exit()

		# If --search argument is not being used, use default value
		else:
			search_obj = "email"

		if ccodes == None:
			ccodes = ['US']
		else:
			ccodes = [x.upper() for x in ccodes]

		return search_obj, base_dir, domain, ccodes, outp

	# Find files under given directory, includes files in subdirectories
	def find_files(self, base_dir):

		file_list = []

		# Loop through directories
		for root, dirs, files in os.walk(base_dir):
			for filename in files:
				file_list.append(os.path.join(root, filename))

		return file_list


	def find_pattern(self):

		# Loop through the list of files
		for file_name in self.file_list:

			# We set archive varible False, because we are not inside an archive
			# With root filename defined, we can freely loop inside archives
			archive = False
			self.root_file = file_name

			# Search every regex pattern defined under search object
			for reg_name, pattern in self.regex_dic.items():

				#if self.search_obj == "phone" and "all" not in self.ccodes or reg_name not in self.ccodes:
				self.regex = re.compile(pattern)

				# Try first if the file is a plain text file
				# TODO: Would be better first to figure out filetype and then based on the type use correct function
				try:
					self.plain_files(reg_name, file_name, archive)

				# If the file couldn't be read by plain_files(), try not_plain_files() function
				except self.exceptions:
					try:
						self.not_plain_files(reg_name, file_name, archive)

					# If the file couldn't be read by not_plain_files() function, file might be a tar/zip
					# so try extracting it
					except self.exceptions:
						try:
							self.tar_files(reg_name, file_name)
						except self.exceptions :
							pass

	# Search patterns in plain text files
	def plain_files(self, reg_name, file_name, archive):
		with open(file_name) as f:

			# Find every match in a file and get rid of duplicates
			match = re.findall(self.regex, f.read())
			unique_values = set(match)
			length = len(unique_values)

			# If at least one match was found, loop through the list of matches and print information necessary
			if length > 0:
				for result in unique_values:

					# If this function is being run by tar_files() function, archive is set to True
					# This will display archive name before the filename in archive
					if archive == False:
						if self.outp == False:
							print(colored(file_name + ": ", "yellow") + str(result) + " - " + reg_name)
						else:
							print(str(result))
					else:
						if self.outp == False:
							print(colored("(" + self.root_file + ") ", "yellow", attrs=['bold']) + colored(os.path.basename(file_name) + ": ", "yellow") + str(result) + " - " + reg_name)
						else:
							print(str(result))

	# Search patterns in files that are not plain text, such as .docx, .xlsx etc.
	def not_plain_files(self, reg_name, file_name, archive):

		# Find every match in a file and get rid of duplicates
		text = textract.process(file_name)
		match = re.findall(self.regex, str(text))
		unique_values = set(match)
		length = len(unique_values)

		# If at least one match was found, loop through the list of matches and print information necessary
		if length > 0:
			for result in unique_values:

				# If this function is being run by tar_files() function, archive is set to True
				# This will display archive name before the filename in archive
				if archive == False:
					if self.outp == False:
						print(colored(file_name + ": ", "yellow") + str(result) + " - " + reg_name)
					else:
						print(str(result))
				else:
					if self.outp == False:
						print(colored("(" + self.root_file + ") ", "yellow", attrs=['bold']) + colored(os.path.basename(file_name) + ": ", "yellow") + str(result) + " - " + reg_name)
					else:
						print(str(result))

	# This function extracts archives such as tar and zip
	def extract_archive(self, file_name, temp_dir):

		# Try first extracting tar file, if it fails try zip
		# TODO: check filetype first and based on the type choose what to do
		try:
			self.extract_tar(file_name, temp_dir)
		except self.exceptions:
			self.extract_zip(file_name, temp_dir)

	# Extracts tarball into a given directory
	def extract_tar(self, file_name, temp_dir):
		
		tar = tarfile.open(file_name, "r")
		for member in tar.getmembers():
			tar.extract(member, temp_dir)

	# Extracts zipfile into a given directory
	def extract_zip(self, file_name, temp_dir):

		with zipfile.ZipFile(file_name, 'r') as zf:
			zf.extractall(temp_dir)

	# This function handles archive extraction and pattern search
	def tar_files(self, reg_name, file_name):

		# Create a temporary directory where an archive will be extracted to
		# and set archive variable to True
		temp_dir = self.temp_dir_base + str(randint(100000000, 1000000000))
		archive = True

		os.makedirs(temp_dir)

		try:
			# Extract archive
			self.extract_archive(file_name, temp_dir)

			# Create a list of files in the temporary directory
			files_in_tar = self.find_files(temp_dir)

			# Loop through the list of files
			for file_in_tar in files_in_tar:

				# Try if the file is plain text file first
				# TODO: Again, based on the type of the file, choose appropriate function
				try:
					self.plain_files(reg_name, file_in_tar, archive)

				# If plain_files() function failed, try not_plain_files()
				except self.exceptions:
					try:
						self.not_plain_files(reg_name, file_in_tar, archive)

					# If the functions above failed, it might be an archive, so start over again
					# leads to nested archives
					except self.exceptions:
						try:
							self.tar_files(reg_name, file_in_tar)
						except self.exceptions:
							pass

		except self.exceptions as e:
			pass

		# Remove the temporary directory and its contents
		finally:
			shutil.rmtree(temp_dir)

if __name__ == "__main__":
	testing = SearchPattern()
