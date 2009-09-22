all : winexe  




winexe : dist/SadFarmer.exe


dist/SadFarmer.exe : SadFarmer.py setup.py icon.ico
	python setup.py py2exe --includes simplejson
	rm -r ./build


clean :
	rm *.cache
	rm *.pyc
	rm *.log
