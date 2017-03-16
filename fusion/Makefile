all:run-fusion


download:
	echo "Downloading reference files into inputs/"
	mkdir -p inputs
	wget -N -P inputs STARFusion-GRCh38gencode23.tar.gz

run-fusion:
	mkdir outputs/fusion
	docker run --rm --name fusion \
	    -v /mnt/data:/data \
            jpfeil/star-fusion:0.0.2 \
            --left_fq samples/{} --right_fq samples/{} --output_dir outputs/fusion \
            --CPU `nproc` \
            --genome_lib_dir inputs/STARFusion-GRCh38gencode23 \
            --run_fusion_inspector
