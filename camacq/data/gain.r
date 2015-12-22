## Author(s): Kalle von Feilitzen, Fredric J & Martin Hjelmare

# Gain calculation script
# Run with "Rscript path/to/script/gain.r path/to/working/dir/
# path/to/histogram-csv-filebase path/to/initialgains/csv-file"
# from linux command line.
# Repeat for each well.

# Gain calculation script
setwd(commandArgs(TRUE)[1])
filebase <- commandArgs(TRUE)[2]
# Initial gain values used
initialgains <- read.csv(commandArgs(TRUE)[3])$gain
gain <- list()
bins <- list()
gains <- list()

green <- 11;    # 11 images
blue <- 18;     # 7 images
yellow <- 25;   # 7 images
red <- 32;      # 7 images
channel <- vector()
channel_name <- vector()
channel <- append(channel, rep(green, green-length(channel)))
channel_name <- append(channel_name, rep('green', green-length(channel_name)))
channel <- append(channel, rep(blue, blue-length(channel)))
channel_name <- append(channel_name, rep('blue', blue-length(channel_name)))
channel <- append(channel, rep(yellow, yellow-length(channel)))
channel_name <- append(channel_name, rep('yellow', yellow-length(channel_name)))
channel <- append(channel, rep(red, red-length(channel)))
channel_name <- append(channel_name, rep('red', red-length(channel_name)))
channels <- unique(channel)


for (i in 1:(length(channels))) {
	bins[[i]] <- vector()
	gains[[i]] <- vector()
}

# Create curve and function for each individual well
for (i in 1:32) {
	# Read histogram CSV file
	csvfile <- paste(filebase, "C", sprintf("%02d", i-1), ".ome.csv", sep="")
	csv <- read.csv(csvfile)
	csv1 <- csv[csv$count>0 & csv$bin>0,]
	bin1 <- csv1$bin
	count1 <- csv1$count
	# Only use values in interval 10-100
	binmax <- tail(csv$bin, n=1)
	csv2 <- csv[csv$count <= 100 & csv$count >= 10 & csv$bin < binmax,]
	bin2 <- csv2$bin
	count2 <- csv2$count
	# Plot values
	test <- 0
	png(filename=paste(filebase, "C", sprintf("%02d", i-1), ".ome.png", sep = ""))
	if (length(bin1) > 0) {
		plot(count1, bin1, log="xy")
	}
	# Fit curve
	sink("/dev/null")	# Suppress output
	curv <- tryCatch(nls(bin2 ~ A*count2^B, start=list(A = 1000, B=-1), trace=T),
									 warning=function(e) NULL,
									 error=function(e) NULL)
	sink()
	if (!is.null(curv)) {
		# Plot curve
		lines(count2, fitted.values(curv), lwd=2, col="green")
		# Find function and save gain value
		func <- function(val, A=coef(curv)[1], B=coef(curv)[2]) {A*val^B}
		chn <- which(channels==channel[i])
		bins[[chn]] <- append(bins[[chn]], func(2))	# 2 is close to 0 but safer
		gains[[chn]] <- append(gains[[chn]], initialgains[i])
	}
	dev.off()
}

# Create curve and function for each channel (multiple wells)
for (i in 1:(length(channels))) {
	bins_c <- bins[[i]]
	gains_c <- gains[[i]]
	png(filename=paste(filebase,
										 channel_name[channels[i]],
										 "_gain.png",
										 sep = ""))
	if (length(bins_c) >= 3) {
		plot(bins_c, gains_c)
		# Remove values not making an upward trend and above bin=600 (Martin Hjelmare)
		point.connected <- 0
		point.start <- 1
		point.end <- 1
		for (m in 1:(length(bins_c)-1)) {
			for (n in (m+1):length(bins_c)) {
				if(bins_c[n] <= 600 & bins_c[n] >= bins_c[n-1]) {
					if((n-m+1) > point.connected) {
						point.connected <- n-m+1
						point.start <- m
						point.end <- n
					}
				}
				else {
					break
				}
			}
		}
		bins_c <- bins_c[point.start:point.end]
		gains_c <- gains_c[point.start:point.end]
	}
	gain[[i]] <- round(initialgains[channels[i]])
	if (length(bins_c) >= 3) {
		# Fit curve
		sink("/dev/null")	# Suppress output
		curv2 <- tryCatch(nls(gains_c ~ C*bins_c^D,
													start=list(C = 1, D=1),
													trace=T),
											warning=function(e) NULL,
											error=function(e) NULL)
		sink()
		# Find function
		if (!is.null(curv2)) {
			func2 <- function(val, A=coef(curv2)[1], B=coef(curv2)[2]) {A*val^B}
			lines(bins_c, fitted.values(curv2), lwd=2, col="green")
			abline(v=binmax)
			gain[[i]] <- round(min(func2(binmax), gain[[i]]))
		}
	}
	dev.off()
}
cat(paste(gain[[1]], gain[[2]], gain[[3]], gain[[4]]))
