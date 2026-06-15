<?php
$files = glob('resources/views/**/*.blade.php', GLOB_BRACE) ?: [];
$files = array_merge($files, glob('resources/views/**/**/*.blade.php', GLOB_BRACE) ?: []);

foreach ($files as $file) {
    $content = file_get_contents($file);
    // Replace unsplash URLs inside asset fallbacks
    $content = preg_replace(
        "/'https:\/\/images\.unsplash\.com\/[^']+'/",
        "asset('placeholder.svg')",
        $content
    );
    file_put_contents($file, $content);
    echo "Updated $file\n";
}
