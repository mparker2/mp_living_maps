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

# convert matrix of probs into factor of highest scoring column for each row
classFromProbs <- function(df) {
  columns <- colnames(df)
  idxmax <- apply(df, MARGIN=1, FUN=which.max)
  return (columns[idxmax])
}