#! /bin/bash

#to run tests of speciifc directory, replace "**/*/*_test.py" with "**/directory/*_test.py"
#to see error messages delete "2> /dev/null"

<<<<<<< HEAD
for filename in **/*/*_test.py; do
    path=${filename//\//.}
    command=${path/.py/}
    python3 -m $command 2> /dev/null && echo failed on $filename
    
done
=======
for filename in **/library/*_test.py; do
    if [[ $filename != *"stream"* ]]; then
	    path=${filename//\//.}
	    command=${path/.py/}
	    python3 -m $command 2> /dev/null || echo failed on $filename
    fi
done
>>>>>>> 408cd0cb6eae7e5ea3d0d6487abcec68237ac8cf
