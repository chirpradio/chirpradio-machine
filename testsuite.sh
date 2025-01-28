#! /bin/bash

#to run tests of speciifc directory, replace "**/*/*_test.py" with "**/directory/*_test.py"
#to see error messages delete "2> /dev/null"

for filename in **/library/*_test.py; do
    path=${filename//\//.}
    command=${path/.py/}
    python3 -m $command 2> /dev/null || echo failed on $filename
    
done