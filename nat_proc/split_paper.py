def split_paper(text):
	"""
	Takes raw text file and splits into a list of strings 
	at each occurence of three or more carriage returns

	At present, may only pick first paragraph of each section depending on how many \n
	"""
	introText =[]
	methText =[]
	discText = []
	chunk =[]
	paras = []
	spl = "\n\n"
	new = text.split(spl)
	for i in new:
		chunk.append(i)

	""" Strip out identical chunks which may 
	be remnant footer or header """

	for i in chunk:
		if i not in paras:
			paras.append(i)
			print i + "\n"

	""" Split based on header terms by word tokens """

	for text in paras:
		wordList = word_tokenize(text.lower())

		for i in wordList:
			if i == 'introduction':
				introText.append(text)
			elif i=='method' or i=='methods':
				methText.append(text)
			elif i=='discussion' or i=='conclusions':
				discText.append(text)

	if introText:
		introOut = introText[0].encode('ascii', errors='backslashreplace')
	else:
		introOut = []
	if methText:
		methOut = methText[0].encode('ascii', errors='backslashreplace')
	else:
		methOut = []
	if discText:
		discOut = discText[0].encode('ascii', errors='backslashreplace')
	else:
		discOut = []

	return introOut, methOut, discOut
