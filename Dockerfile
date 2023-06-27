FROM cellprofiler/cellprofiler

# Install Python3.7
RUN apt-get update && apt-get install -y python3.7 python3.7-dev python3.7-venv
RUN python3.7 -m pip install --upgrade pip && python3.7 -m pip install Cython

# ------------------------------------------------------------------------------
# Install Cytomine python client
RUN git clone https://github.com/cytomine-uliege/Cytomine-python-client.git && \
    cd Cytomine-python-client && git checkout tags/v2.7.3 && \ 
    python3.7 -m pip install . && \
    cd .. && \
    rm -r Cytomine-python-client

# ------------------------------------------------------------------------------
# Install BIAFLOWS utilities (annotation exporter, compute metrics, helpers,...)
RUN apt-get update && apt-get install libgeos-dev -y && apt-get clean
RUN git clone https://github.com/Neubias-WG5/biaflows-utilities.git && \
    cd biaflows-utilities/ && git checkout tags/v0.9.1 && python3.7 -m pip install .

# install utilities binaries
RUN chmod +x biaflows-utilities/bin/*
RUN cp biaflows-utilities/bin/* /usr/bin/ && \
    rm -r biaflows-utilities

# ------------------------------------------------------------------------------
# Add repository files: wrapper, command and descriptor
RUN mkdir /app
ADD wrapper.py /app/wrapper.py
ADD PLA-dot-counting-with-speckle-enhancement.cppipe /app/PLA-dot-counting-with-speckle-enhancement.cppipe
ADD descriptor.json /app/descriptor.json

ENTRYPOINT ["python3.7","/app/wrapper.py"]
