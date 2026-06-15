<?php
$files = glob('resources/lang/*/*.php');
foreach ($files as $file) {
    $content = file_get_contents($file);
    $content = str_ireplace('Ram Interior', 'Yadav Interior', $content);
    file_put_contents($file, $content);
    echo "Updated $file\n";
}
