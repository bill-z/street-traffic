#!/bin/bash

# Upload all images in photos folder to AWS S3 bucket for speed data images.
# After uploading move images from photos to uploaded. 
# (for use on raspberry pi -- assumes AWS CLI installed and configured)

PROJECT_DIR=/home/pi/Projects/street-traffic
BUCKET_NAME=speed-data-images211101-dev
AWS_PROFILE=traffic
AWS=/home/pi/.local/bin/aws

$AWS s3 cp\
 --recursive\
 --profile $AWS_PROFILE\
 $PROJECT_DIR/photos\
 s3://$BUCKET_NAME/public

mv $PROJECT_DIR/photos/* $PROJECT_DIR/uploaded
