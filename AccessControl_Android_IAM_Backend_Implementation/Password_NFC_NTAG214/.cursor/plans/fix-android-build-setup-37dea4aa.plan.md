<!-- 37dea4aa-7877-4c19-9895-77d02fe1d925 a086e7ad-8d5a-400a-8950-99d84bc13e75 -->
# Fix Android Build Configuration

## Problem

The project is missing critical configuration files that tell Gradle where the Android SDK is located and which Gradle version to use.

## Solution

### 1. Create `local.properties`

Create file at project root with Android SDK path:

```
sdk.dir=C\:\\Users\\jaque\\AppData\\Local\\Android\\Sdk
```

This tells Gradle where to find the Android SDK on your system.

### 2. Create `gradle-wrapper.properties`

Create file at `gradle/wrapper/gradle-wrapper.properties` with:

```
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.2-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
```

This specifies Gradle version 8.2 (compatible with Android Gradle Plugin 8.2.0 already in build.gradle.kts).

### 3. Verify JDK Settings

After creating these files, you should:

- Ensure Android Studio is using JDK 17 (not JDK 25)
- File → Project Structure → SDK Location → Gradle JDK → Select JDK 17
- If JDK 17 is not available, download it through Android Studio

### 4. Sync Project

After files are created, sync the project with Gradle files.

## Files to Create

1. `local.properties` - SDK location
2. `gradle/wrapper/gradle-wrapper.properties` - Gradle version

These files are typically gitignored and auto-generated, but need manual creation in this case.

### To-dos

- [ ] Create local.properties file with Android SDK path
- [ ] Create gradle-wrapper.properties file with Gradle 8.2 configuration