dist/SadFarmer.exe : SadFarmer.py setup.py icon.ico
	python setup.py py2exe --includes simplejson
