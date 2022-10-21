# Simple command line running of pipelines used in Treehouse
#
# Generates expression, fusions, and variants folders in outputs

# Look for any files with 1 or 2 followed by any non-numeric till the end
# Alternatively, look for R1_001.fastq.gz and R2 -- most common format we use.
R1 = $(shell find samples -iregex ".+\(1[^0-9]*\|R1_001.fastq.gz\)$$" | head -1)
R2 = $(shell find samples -iregex ".+\(2[^0-9]*\|R2_001.fastq.gz\)$$" | head -1)

REF_BASE ?= "http://hgdownload.soe.ucsc.edu/treehouse/reference"

all: reference expression qc fusions variants jfkm verify

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


reference_ercc:
	echo "Downloading reference files including ERCC transcripts from $(REF_BASE)..."
	mkdir -p references
	wget -N -P references $(REF_BASE)/GRCh38_gencode23_ERCC92_transcripts.idx
	wget -N -P references $(REF_BASE)/starindex_GRCh38_gencode23_ERCC92.tar.gz
	wget -N -P references $(REF_BASE)/rsem_ref_GRCh38_gencode23_ERCC92.tar.gz
	wget -N -P references $(REF_BASE)/hg38_GENCODE_v23_ERCC92.reseqc.bed
	wget -N -P references $(REF_BASE)/STARFusion-GRCh38gencode23.tar.gz
	wget -N -P references $(REF_BASE)/GCA_000001405.15_GRCh38_no_alt_analysis_set.dict
	wget -N -P references $(REF_BASE)/GCA_000001405.15_GRCh38_no_alt_analysis_set.fa
	wget -N -P references $(REF_BASE)/GCA_000001405.15_GRCh38_no_alt_analysis_set.fa.fai
	echo "Verifying reference files..."
	md5sum -c md5/references_ercc.md5
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
	echo "Running expression pipeline 3.3.4-1.12.3 on $(R1) and $(R2)"
	mkdir -p outputs/expression
	docker run --rm \
		-v $(shell pwd)/outputs/expression:$(shell pwd)/outputs/expression \
		-v $(shell pwd)/samples:/samples \
		-v $(shell pwd)/references:/references \
		-v /var/run/docker.sock:/var/run/docker.sock \
		quay.io/ucsc_cgl/rnaseq-cgl-pipeline@sha256:785eee9f750ab91078d84d1ee779b6f74717eafc09e49da817af6b87619b0756 \
			--save-bam \
			--star /references/starIndex_hg38_no_alt.tar.gz \
			--rsem /references/rsem_ref_hg38_no_alt.tar.gz \
			--kallisto /references/kallisto_hg38.idx \
			--work_mount $(shell pwd)/outputs/expression \
			--sample-paired $(R1),$(R2)

expression_ercc:
	echo "Running expression pipeline 3.3.4-1.12.3, with ERCC transcripts, debug output suppressed, on $(R1) and $(R2)"
	mkdir -p outputs/expression
	docker run --rm \
		-v $(shell pwd)/outputs/expression:$(shell pwd)/outputs/expression \
		-v $(shell pwd)/samples:/samples \
		-v $(shell pwd)/references:/references \
		-v /var/run/docker.sock:/var/run/docker.sock \
		quay.io/ucsc_cgl/rnaseq-cgl-pipeline@sha256:785eee9f750ab91078d84d1ee779b6f74717eafc09e49da817af6b87619b0756 \
			--save-bam \
			--star /references/starindex_GRCh38_gencode23_ERCC92.tar.gz \
			--rsem /references/rsem_ref_GRCh38_gencode23_ERCC92.tar.gz \
			--kallisto /references/GRCh38_gencode23_ERCC92_transcripts.idx \
			--work_mount $(shell pwd)/outputs/expression \
			--sample-paired $(R1),$(R2)
qc:
	echo "Running bam-umend-qc 1.1.1 pipeline on sorted bam from expression"
	mkdir -p outputs/qc
	docker run --rm \
	  -v `pwd`/$(shell find outputs/expression/*.bam):/inputs/sample.bam \
		-v $(shell pwd)/outputs/qc:/tmp \
		-v $(shell pwd)/outputs/qc:/outputs \
		ucsctreehouse/bam-umend-qc@sha256:5f286d72395fcc5085a96d463ae3511554acfa4951aef7d691bba2181596c31f \
			/inputs/sample.bam /outputs

qc_ercc:
	echo "Running bam-mend-qc v2.0.2 pipeline, with ERCC transcripts, on sorted bam from expression"
	mkdir -p outputs/qc
	docker run --rm \
	  -v `pwd`/$(shell find outputs/expression/*.bam):/inputs/sample.bam \
		-v $(shell pwd)/outputs/qc:/tmp \
		-v $(shell pwd)/outputs/qc:/outputs \
		ucsctreehouse/bam-mend-qc@sha256:1c3c62731eb7e6bbfcba4600807022e250a9ee5874477d115939a5d33f39e39f \
			/inputs/sample.bam /outputs hg38_GENCODE_v23_ERCC92.reseqc.bed

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
	  -v `pwd`/$(shell find outputs/qc/*.bam):/inputs/sample.bam \
		-v $(shell pwd)/outputs/variants:/outputs \
		ucsctreehouse/mini-var-call@sha256:197642937956ae73465ad2ef4b42501681ffc3ef07fecb703f58a3487eab37ff \
			/references/GCA_000001405.15_GRCh38_no_alt_analysis_set.fa \
			/inputs/sample.bam \
			/outputs

jfkm:
	echo "Running Jellyfish - Km pipeline on $(R1) and $(R2)"
	mkdir -p outputs/jfkm
	docker run --rm \
	       -v $(shell pwd)/samples:/data/samples \
	       -v $(shell pwd)/outputs/jfkm:/data/outputs \
               jpfeil/jfkm:0.1.0 \
                        --CPU `nproc` \
                        --FLT3-ITD \
                        --left-fq $(R1) \
                        --right-fq $(R2) \
                        --output-dir outputs

pizzly:
	echo "Running Pizzly 0.37.3 on Kallisto/fusion.txt from expression"
	mkdir -p outputs/pizzly
	docker run --rm \
	    -v $(shell pwd)/outputs/expression/Kallisto:/Kallisto:ro \
	    -v $(shell pwd)/outputs/pizzly:/data \
	    ucsctreehouse/pizzly@sha256:43efb2faf95f9d6bfd376ce6b943c9cf408fab5c73088023d633e56880ac1ea8 \
	        -f /Kallisto/fusion.txt \
	        -a /Kallisto/abundance.h5

verify:
	echo "Verifying md5 of output of TEST file"
	tar -xOzvf outputs/expression/TEST_R1merged.tar.gz TEST_R1merged/RSEM/rsem_genes.results | md5sum -c md5/expression.md5
	cut -f 1 outputs/fusions/star-fusion-non-filtered.final | sort | md5sum -c md5/fusions.md5
	tail -n 10 outputs/variants/mini.ann.vcf | md5sum -c md5/variants.md5
