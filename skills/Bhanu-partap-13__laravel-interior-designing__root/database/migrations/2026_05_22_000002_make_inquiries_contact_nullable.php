<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('inquiries', function (Blueprint $table) {
            if (Schema::hasColumn('inquiries', 'visitor_name')) {
                $table->string('visitor_name')->nullable()->change();
            }
            if (Schema::hasColumn('inquiries', 'visitor_email')) {
                $table->string('visitor_email')->nullable()->change();
            }
        });
    }

    public function down(): void
    {
        Schema::table('inquiries', function (Blueprint $table) {
            if (Schema::hasColumn('inquiries', 'visitor_name')) {
                $table->string('visitor_name')->nullable(false)->change();
            }
            if (Schema::hasColumn('inquiries', 'visitor_email')) {
                $table->string('visitor_email')->nullable(false)->change();
            }
        });
    }
};
