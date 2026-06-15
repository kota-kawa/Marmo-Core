<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('designers', function (Blueprint $table) {
            $table->string('education', 160)->nullable()->after('portfolio_url');
            $table->text('certifications')->nullable()->after('education');
        });
    }

    public function down(): void
    {
        Schema::table('designers', function (Blueprint $table) {
            $table->dropColumn(['education', 'certifications']);
        });
    }
};
