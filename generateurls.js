const fs = require('fs');
const path = require('path');

const directoryPath =  "" // visualizations folder
const outputFile = 'imageBase64.json';

fs.readdir(directoryPath, (err, files) => {
  if (err) {
    return console.error('Unable to scan directory: ' + err);
  }

  const imageBase64Array = files.map((file) => {
    const filePath = path.join(directoryPath, file);
    const fileData = fs.readFileSync(filePath);
    return fileData.toString('base64');
  });

  fs.writeFileSync(outputFile, JSON.stringify(imageBase64Array, null, 2));
  console.log('Base64 conversion complete. Check imageBase64.json.');
});
