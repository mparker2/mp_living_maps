## Helper functions

randomSubset <- function(df, frac.training) {
  frac <- floor((nrow(df) * frac.training))
  subset <- sample(nrow(df), size=frac)
  return (subset)
}

# Produces user / producer accuracy
# depending on whether rowSums or colSums is passed
userProducerAccuracy <- function(i, confusion.table, f=rowSums) {
  tots <- f(confusion.table)
  # replace NaNs with 0 if there is no data for the row/col
  if (tots[i] == 0) {
    return(0.0)
  }
  else {
    return (confusion.table[i,i]/tots[i] * 100)
  }
}

# produce confusion matrix and user / produce accuracies
confusionMatrix <- function(user, producer) {
  user <- as.factor(user)
  producer <- as.factor(producer)
  # if user and producer are different lengths, something is wrong!
  stopifnot(length(user) == length(producer))
  
  n <- length(levels(user))
  confusion.table <- table(producer, user)
  
  range <- as.matrix(1:n)
  # total accuracy is the sum of the diagonal divided by the sum of the whole
  total.accuracy <- sum(diag(confusion.table)) / sum(confusion.table) * 100
  user.accuracy <- apply(range, MARGIN=1, FUN=userProducerAccuracy,
                         confusion.table=confusion.table, f=colSums)
  producer.accuracy <- apply(range, MARGIN=1, FUN=userProducerAccuracy,
                             confusion.table=confusion.table, f=rowSums)
  names(user.accuracy) <- colnames(confusion.table)
  names(producer.accuracy) <- rownames(confusion.table)
  
  return (list(table=confusion.table,
               user.accuracy=user.accuracy,
               producer.accuracy=producer.accuracy,
               total.accuracy=total.accuracy))
}

getLastStringElement <- function(col, splitchar='_') {
  col <- as.character(col)
  split <- strsplit(col, split=splitchar)
  string.elements <- character(length(col))
  for (i in 1:length(col)) {
    string.elements[i] <- split[[i]][length(split[[i]])]
  }
  return (string.elements)
}


# convert matrix of probs into factor of highest scoring column for each row
classFromProbs <- function(df) {
  columns <- colnames(df)
  idxmax <- apply(df, MARGIN=1, FUN=which.max)
  return (columns[idxmax])
}

# do not read stringsAsFactors yet as subsetting and removing all instances of
# a level from the data.frame will cause randomForest to raise error.
zonal.stats <- read.table('D:/Living Maps/Zonal_stats/zonal_stats_merged.tsv',
                          sep='\t', header=TRUE, stringsAsFactors=FALSE)
# add perimeter / area variable
zonal.stats['perimeter_area_ratio'] <- zonal.stats$perimeter / zonal.stats$area



# remove low confidence training points - try conf <= 2 first
zonal.stats <- zonal.stats[zonal.stats$confidence <= 2,]

# replace nans with column median
for (i in 4:ncol(zonal.stats)) {
  zonal.stats[is.na(zonal.stats[,i]), i] <- median(zonal.stats[,i], na.rm = TRUE)
}
# set very large, negative values in SLOPE, HEIGHT and ASPECT to be zero
zonal.stats[zonal.stats < 0] <- 0

# now we can convert strings to factors
zonal.stats <- as.data.frame(unclass(zonal.stats), stringsAsFactors=TRUE)

# fit random forests with different mtry to determine optimum parameter
library(randomForest)

OOB.error <- double(ncol(zonal.stats)-3)
for (mtry in 1:(ncol(zonal.stats)-3)) {
  set.seed(1001)
  fit.rf <- randomForest(broadclass ~ .,
                         data=zonal.stats[,c(1, 4:ncol(zonal.stats))],
                         mtry=mtry,
                         ntree=800)
  OOB.error[mtry] = 1 - sum(diag(fit.rf$confusion)) / sum(fit.rf$confusion)
  cat(mtry, " ")
}
plot(OOB.error, type='l')

# best mtry is around 4-6

set.seed(10)
fit.rf <- randomForest(broadclass ~ .,
                       data=zonal.stats[,c(1, 4:ncol(zonal.stats))],
                       mtry=5,
                       ntree=800)

# fit gradient boosted machine - we can use this to examine the importance
# of different variables
library(gbm)

frac <- randomSubset(zonal.stats, 0.8)
zs.train <- zonal.stats[frac,]
zs.test <- zonal.stats[-frac,]

fit.gbm <- gbm(broadclass ~ .,
               data=zs.train[,c(1, 4:ncol(zonal.stats))],
               distribution='multinomial',
               n.trees=1000,
               shrinkage=0.01,
               interaction.depth=4,
               cv.folds=2)

ntrees <- gbm.perf(fit.gbm)
predicted.gbm <- predict(fit.gbm,
                         newdata=zs.test[,c(1, 4:ncol(zonal.stats))],
                         type='response',
                         n.trees=ntrees)
predicted.gbm.classes <- classFromProbs(predicted.gbm)
predicted.gbm.classes <- factor(predicted.gbm.classes, levels=levels(zs.test$broadclass))
confusionMatrix(zs.test$broadclass, predicted.gbm.classes)

# look at the most important variables:
summary(fit.gbm)
# S2_summer RedEdge5_mean and SWIR2_mean are most important by a long way
# maximum slope and minimum height are also important, plus winter SAR data.

# lets look at some of these variables
library(ggplot2)

plotviolin <- function(column) {
  g <- ggplot(zonal.stats, aes_string('broadclass', column))
  g <- g + geom_violin()
  g <- g + theme(axis.text.x = element_text(angle = 45, hjust = 1))
  g
}

# RedEdge5 looks important for classifying water
plotviolin('S2_summer_RedEdge5_mean')

# as does SWIR2
plotviolin('S2_summer_SWIR2_mean')

# which types of features are the best
#i.e. do max, min and std add anything to the model
fit.gbm.summary <- summary(fit.gbm)

fit.gbm.summary$feature_type <- getLastStringElement(fit.gbm.summary$var)
ggplot(fit.gbm.summary, aes(feature_type, rel.inf)) + geom_point()

# derived parameters (i.e. perimeter / area ratio) can be more useful than
# the individual parameters alone. Min and max do add to model.