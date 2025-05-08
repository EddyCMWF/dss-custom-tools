FROM continuumio/miniconda3

WORKDIR /src/dss-custom-tools

COPY environment.yml /src/dss-custom-tools/

RUN conda install -c conda-forge gcc python=3.11 \
    && conda env update -n base -f environment.yml

COPY . /src/dss-custom-tools

RUN pip install --no-deps -e .
