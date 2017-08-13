# Simple command line running of pipelines used in Treehouse

R1 = $(shell ls samples/*R1* | head -1)
R2 = $(shell ls samples/*R2* | head -1)
BAM = $(shell find outputs/*sortedByCoord*  -printf "%f\n")

# REF_BASE = "http://hgdownload.soe.ucsc.edu/treehouse/reference"
REF_BASE = "http://ceph-gw-01.pod/references"

all: reference expression fusion variant verify

reference:
	echo "Downloading reference files..."
	mkdir -p references samples outputs
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

expression:
	echo "Running expression and qc pipeline on $(R1) and $(R2)"
	docker run --rm \
		-v $(shell pwd)/outputs:$(shell pwd)/outputs \
		-v $(shell pwd)/samples:/samples \
		-v $(shell pwd)/references:/references \
		-v /var/run/docker.sock:/var/run/docker.sock \
		quay.io/ucsc_cgl/rnaseq-cgl-pipeline:3.3.4-1.12.3 \
			--logDebug \
			--bamqc \
			--save-bam \
			--star /references/starIndex_hg38_no_alt.tar.gz \
			--rsem /references/rsem_ref_hg38_no_alt.tar.gz \
			--kallisto /references/kallisto_hg38.idx \
			--work_mount $(shell pwd)/outputs \
			--sample-paired $(R1),$(R2)

fusion:
	echo "Running fusion pipeline on $(R1) and $(R2)"
	mkdir -p outputs/fusion
	docker run --rm \
		-v $(shell pwd)/outputs:/data/outputs \
		-v $(shell pwd)/samples:/data/samples \
		-v $(shell pwd)/references:/data/references \
		ucsctreehouse/fusion:0.1.0 \
			--left-fq $(R1) \
			--right-fq $(R2) \
			--output-dir outputs/fusion \
			--CPU `nproc` \
			--genome-lib-dir references/STARFusion-GRCh38gencode23 \
			--run-fusion-inspector

variant:
	echo "Running rna variant calling on sorted bam from expression WARNING: EXPERIMENTAL"
	docker run --rm \
		-v $(shell pwd)/references:/data/ref \
		-v $(shell pwd)/outputs:/data/work \
		-e refgenome=GCA_000001405.15_GRCh38_no_alt_analysis_set.fa \
		-e input=$(BAM) linhvoyo/gatk_rna_variant_v2

verify:
	echo "Verifying md5 of output of test file (FAIL. is normal as its a small number of reads)"
	tar -xOzvf outputs/TEST_R1merged.tar.gz FAIL.TEST_R1merged/RSEM/rsem_genes.results | md5sum -c md5/expression.md5
	cut -f 1 outputs/fusion/star-fusion-non-filtered.final | sort | md5sum -c md5/fusion.md5
