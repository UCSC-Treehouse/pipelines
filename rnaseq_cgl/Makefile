download:
	mkdir -p scratch
	wget -N -P inputs https://treehouse.blob.core.windows.net/reference/kallisto_hg38.idx
	wget -N -P inputs https://treehouse.blob.core.windows.net/reference/starIndex_hg38_no_alt.tar.gz
	wget -N -P inputs https://treehouse.blob.core.windows.net/reference/rsem_ref_hg38_no_alt.tar.gz

test:
	docker run \
		-v $(shell pwd)/scratch:$(shell pwd)/scratch \
		-v $(shell pwd)/samples:/samples \
		-v $(shell pwd)/inputs:/inputs \
		-v /var/run/docker.sock:/var/run/docker.sock \
		quay.io/ucsc_cgl/rnaseq-cgl-pipeline:2.0.8 \
		--star /inputs/starIndex_hg38_no_alt.tar.gz \
		--rsem /inputs/rsem_ref_hg38_no_alt.tar.gz \
		--kallisto /inputs/kallisto_hg38.idx \
		--samples /samples/TEST.tar

verify:
	md5sum -c TEST.tar.gz.md5
