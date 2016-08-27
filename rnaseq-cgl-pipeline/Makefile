# Treehouse RNA Seq Pipeline
# See https://github.com/BD2KGenomics/cgl-docker-lib/tree/master/rnaseq-cgl-pipeline

all: download test verify

download:
	# Download reference files
	wget -N -P inputs https://treehouse.blob.core.windows.net/reference/kallisto_hg38.idx
	wget -N -P inputs https://treehouse.blob.core.windows.net/reference/starIndex_hg38_no_alt.tar.gz
	wget -N -P inputs https://treehouse.blob.core.windows.net/reference/rsem_ref_hg38_no_alt.tar.gz

test:
	# Run the test file through the pipeline
	docker run \
		-v $(shell pwd)/outputs:$(shell pwd)/outputs \
		-v $(shell pwd)/samples:/samples \
		-v $(shell pwd)/inputs:/inputs \
		-v /var/run/docker.sock:/var/run/docker.sock \
		quay.io/ucsc_cgl/rnaseq-cgl-pipeline:2.0.8 \
		--star /inputs/starIndex_hg38_no_alt.tar.gz \
		--rsem /inputs/rsem_ref_hg38_no_alt.tar.gz \
		--kallisto /inputs/kallisto_hg38.idx \
		--samples /samples/TEST.tar

verify:
	# Verify the output of the test run
	tar -xOzvf TEST0.tar.gz TEST/RSEM/rsem.genes.norm_counts.tab | md5sum -c TEST.md5

run:
	# Run all files in the samples folder through the pipeline
	docker run \
		-v $(shell pwd)/outputs:$(shell pwd)/outputs \
		-v $(shell pwd)/samples:/samples \
		-v $(shell pwd)/inputs:/inputs \
		-v /var/run/docker.sock:/var/run/docker.sock \
		quay.io/ucsc_cgl/rnaseq-cgl-pipeline:2.0.8 \
		--star /inputs/starIndex_hg38_no_alt.tar.gz \
		--rsem /inputs/rsem_ref_hg38_no_alt.tar.gz \
		--kallisto /inputs/kallisto_hg38.idx \
		--samples /samples/*
