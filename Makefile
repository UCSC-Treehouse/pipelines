# Simple command line running of pipelines used in Treehouse
#
# Generates expression, fusions, and variants folders in outputs

R1 = $(shell find samples -iregex ".*?[_1|_R1]\..*?" | head -1)
R2 = $(shell find samples -iregex ".*?[_2|_R2]\..*?" | head -1)

REF_BASE ?= "http://hgdownload.soe.ucsc.edu/treehouse/reference"

all: reference expression fusions variants verify

reference:
	echo "Downloading reference files from $(REF_BASE)..."
	mkdir -p references
	wget -N -P references $(REF_BASE)/kallisto_hg38.idx
	wget -N -P references $(REF_BASE)/starIndex_hg38_no_alt.tar.gz
	wget -N -P references $(REF_BASE)/rsem_ref_hg38_no_alt.tar.gz
	wget -N -P references $(REF_BASE)/STARFusion-GRCh38gencode23.tar.gz
	wget -N -P references $(REF_BASE)/GCA_000001405.15_GRCh38_no_alt_analysis_set.dict
	wget -N -P references $(REF_BASE)/GCA_000001405.15_GRCh38_no_alt_analysis_set.fa
	wget -N -P references $(REF_BASE)/GCA_000001405.15_GRCh38_no_alt_analysis_set.fa.fai
	echo "Verifying reference files..."
	md5sum -c md5/references.md5
	if [ ! -d "references/STARFusion-GRCh38gencode23" ]; then \
		echo "Unpacking fusion reference files..."; \
		tar -zxsvf references/STARFusion-GRCh38gencode23.tar.gz -C references --skip-old-files; \
	fi

checksums:
	echo "Calculating md5 of input sample files"
	mkdir -p outputs/checksums
	docker run --rm \
		-v $(shell pwd)/outputs:/data/outputs \
		-v $(shell pwd)/samples:/data/samples \
		-w /data/samples \
		alpine@sha256:ccba511b1d6b5f1d83825a94f9d5b05528db456d9cf14a1ea1db892c939cda64 \
			/bin/sh -c "md5sum * > /data/outputs/checksums/md5"

expression:
	echo "Running expression and qc pipeline 3.3.4-1.12.3 on $(R1) and $(R2)"
	mkdir -p outputs/expression
	docker run --rm \
		-v $(shell pwd)/outputs/expression:$(shell pwd)/outputs/expression \
		-v $(shell pwd)/samples:/samples \
		-v $(shell pwd)/references:/references \
		-v /var/run/docker.sock:/var/run/docker.sock \
		quay.io/ucsc_cgl/rnaseq-cgl-pipeline@sha256:785eee9f750ab91078d84d1ee779b6f74717eafc09e49da817af6b87619b0756 \
			--bamqc \
			--save-bam \
			--star /references/starIndex_hg38_no_alt.tar.gz \
			--rsem /references/rsem_ref_hg38_no_alt.tar.gz \
			--kallisto /references/kallisto_hg38.idx \
			--work_mount $(shell pwd)/outputs/expression \
			--sample-paired $(R1),$(R2)

fusions:
	echo "Running fusion 0.1.0 pipeline on $(R1) and $(R2)"
	mkdir -p outputs/fusions
	docker run --rm \
		-v $(shell pwd)/outputs:/data/outputs \
		-v $(shell pwd)/samples:/data/samples \
		-v $(shell pwd)/references:/data/references \
		ucsctreehouse/fusion@sha256:3faac562666363fa4a80303943a8f5c14854a5f458676e1248a956c13fb534fd \
			--left-fq $(R1) \
			--right-fq $(R2) \
			--output-dir outputs/fusions \
			--CPU `nproc` \
			--genome-lib-dir references/STARFusion-GRCh38gencode23 \
			--run-fusion-inspector

variants:
	echo "Running rna variant calling on sorted bam from expression"
	mkdir -p outputs/variants
	docker run --rm \
		-v $(shell pwd)/references:/references \
	  -v `pwd`/$(shell find outputs/expression/*sortedByCoord*):/inputs/sample.bam \
		-v $(shell pwd)/outputs/variants:/outputs \
		ucsctreehouse/mini-var-call@sha256:197642937956ae73465ad2ef4b42501681ffc3ef07fecb703f58a3487eab37ff \
			/references/GCA_000001405.15_GRCh38_no_alt_analysis_set.fa \
			/inputs/sample.bam \
			/outputs

verify:
	echo "Verifying md5 of output of TEST file"
	tar -xOzvf outputs/expression/TEST_R1merged.tar.gz FAIL.TEST_R1merged/RSEM/rsem_genes.results | md5sum -c md5/expression.md5
	cut -f 1 outputs/fusions/star-fusion-non-filtered.final | sort | md5sum -c md5/fusions.md5
	tail -n 10 outputs/variants/mini.ann.vcf | md5sum -c md5/variants.md5
