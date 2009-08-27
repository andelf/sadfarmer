# make file



dist/SadFarmer.exe : SadFarmer.py setup.py icon.ico
	python setup.py py2exe -q --includes simplejson
	rm -r ./build

    
clean:
	rm -r ./build
	rm -r ./dist