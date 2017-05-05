# Simple command line running of pipelines used in Treehouse

R1 = $(shell ls samples/*R1* | head -1)
R2 = $(shell ls samples/*R2* | head -1)

all: references expression fusion verify

references:
	echo "Downloading reference files..."
	mkdir -p references
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/kallisto_hg38.idx
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/starIndex_hg38_no_alt.tar.gz
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/rsem_ref_hg38_no_alt.tar.gz
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/STARFusion-GRCh38gencode23.tar.gz
	wget -N -P references http://ceph-gw-01.pod/references/GCA_000001405.15_GRCh38_no_alt_analysis_set.fa
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
		quay.io/ucsc_cgl/rnaseq-cgl-pipeline:3.2.1-1 \
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

variants:
	echo "Running rna variant calling on sorted bam from expression"
	docker run --rm \
		-v $(shell pwd)/references:/data/ref \
		-v $(shell pwd)/outputs:/data/work \
		-e refgenome=GCA_000001405.15_GRCh38_no_alt_analysis_set.fa \
		-e input=TEST_R1merged.sortedByCoord.md.bam linhvoyo/gatk_rna_variant_v2

verify:
	echo "Verifying md5 of output of test file (FAIL. is normal as its a small number of reads)"
	tar -xOzvf outputs/TEST_R1merged.tar.gz FAIL.TEST_R1merged/RSEM/rsem_genes.results | md5sum -c md5/expression.md5
	cut -f 1 outputs/fusion/star-fusion.fusion_candidates.final | sort | md5sum -c md5/fusion.md5
