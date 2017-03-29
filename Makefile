# Simple command line running of pipelines used in Treehouse

SAMPLES = $(shell ls -d samples/* | sed -e 's/samples/\/samples/g')

download:
	echo "Downloading reference files..."
	mkdir -p references
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/kallisto_hg38.idx
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/starIndex_hg38_no_alt.tar.gz
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/rsem_ref_hg38_no_alt.tar.gz
	wget -N -P references http://hgdownload.soe.ucsc.edu/treehouse/reference/STARFusion-GRCh38gencode23.tar.gz
	(cd references && md5sum -c references.md5)

expression:
	# Run the pipeline on all files listed in SAMPLES
	echo "Running expression and qc pipeline on $(SAMPLES)"
	docker run \
		-v $(shell pwd)/outputs:$(shell pwd)/outputs \
		-v $(shell pwd)/samples:/samples \
		-v $(shell pwd)/references:/references \
		-v /tmp:/work \
		-v /var/run/docker.sock:/var/run/docker.sock \
		quay.io/ucsc_cgl/rnaseq-cgl-pipeline:3.2.1-1 \
		--save-wiggle --save-bam \
		--star /references/starIndex_hg38_no_alt.tar.gz \
		--rsem /references/rsem_ref_hg38_no_alt.tar.gz \
		--kallisto /references/kallisto_hg38.idx \
		--work_mount /work \
		--sample-paired /samples

fusion:
	mkdir outputs/fusion
	docker run --rm --name fusion \
	    -v /mnt/data:/data \
            jpfeil/star-fusion:0.0.2 \
            --left_fq samples/{} --right_fq samples/{} --output_dir outputs/fusion \
            --CPU `nproc` \
            --genome_lib_dir inputs/STARFusion-GRCh38gencode23 \
            --run_fusion_inspector

verify:
	echo "Verifying output of test file"
	tar -xOzvf outputs/TEST.tar.gz TEST/RSEM/rsem.genes.norm_counts.tab | md5sum -c outputs/TEST.md5
