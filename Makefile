# Simple command line running of pipelines used in Treehouse

R1 = $(shell ls samples/*R1* | head -1)
R2 = $(shell ls samples/*R2* | head -1)

all: download expression fusion verify

download:
	echo "Downloading reference files..."
	mkdir -p references
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/kallisto_hg38.idx
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/starIndex_hg38_no_alt.tar.gz
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/rsem_ref_hg38_no_alt.tar.gz
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/STARFusion-GRCh38gencode23.tar.gz
	md5sum -c md5/references.md5
	echo "Unpacking fusion reference files..."
	tar -zxsvf references/STARFusion-GRCh38gencode23.tar.gz -C references --skip-old-files

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
			--star /references/starIndex_hg38_no_alt.tar.gz \
			--rsem /references/rsem_ref_hg38_no_alt.tar.gz \
			--kallisto /references/kallisto_hg38.idx \
			--work_mount $(shell pwd)/outputs \
			--sample-paired $(R1),$(R2)

fusion:
	echo "Running fusion pipeline on $(R1) and $(R2)"
	docker run --rm \
		-v $(shell pwd)/outputs:/data/outputs \
		-v $(shell pwd)/samples:/data/samples \
		-v $(shell pwd)/references:/data/references \
        jpfeil/star-fusion:0.0.2 \
			--left_fq $(R1) \
			--right_fq $(R2) \
			--output_dir outputs/fusion \
			--CPU `nproc` \
			--genome_lib_dir references/STARFusion-GRCh38gencode23 \
			--run_fusion_inspector

verify:
	echo "Verifying md5 of output of test file (FAIL. is normal as its a small number of reads)"
	tar -xOzvf outputs/TEST_R1merged.tar.gz FAIL.TEST_R1merged/RSEM/rsem_genes.results | md5sum -c md5/expression.md5
	cut -f 1 outputs/fusion/star-fusion.fusion_candidates.final | sort | md5sum -c md5/fusion.md5
