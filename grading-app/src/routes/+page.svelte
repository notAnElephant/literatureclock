<script>
    import { onMount } from 'svelte';
    import { fade, fly } from 'svelte/transition';

    let entry = null;
    let loading = true;
    let rating = 0;
    let timeClass = null; // 'am', 'pm', 'ambiguous'
    let error = null;
    let stats = { total_entries: 0, voted_entries: 0, average_rating: 0 };
    let hasVotedRating = false;
    
    // Time Correction
    let correctedTime = '';
    let isEditingTime = false;

    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            if (res.ok) {
                stats = await res.json();
            }
        } catch (e) {
            console.error("Stats fetch failed", e);
        }
    }

    async function fetchEntry() {
        loading = true;
        entry = null;
        rating = 0;
        timeClass = null;
        error = null;
        hasVotedRating = false;
        isEditingTime = false;
        correctedTime = '';
        
        try {
            const res = await fetch('/api/entries');
            if (res.ok) {
                const data = await res.json();
                if (data && !data.error) {
                    entry = data;
                } else {
                    error = data?.error || "No entry found";
                }
            } else {
                error = "Failed to fetch";
            }
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function submitVote(isDeny = false) {
        if (!entry) return;
        
        if (isDeny) {
            // No validation needed for deny
        } else {
            if (!timeClass) {
                alert("Please select AM, PM, or Ambiguous");
                return;
            }
            if (rating === 0) {
                alert("Please rate the quote (1-5 stars) or use Deny");
                return;
            }
        }
        
        const finalRating = isDeny ? 0 : rating;
        const finalTimeClass = isDeny ? (timeClass || 'ambiguous') : timeClass;
        
        // Use corrected time if provided and editing was active or value exists
        const finalTime = (correctedTime && correctedTime !== entry.valid_times[0]) ? correctedTime : null;

        const voteData = { 
            entry_id: entry.id, 
            rating: finalRating, 
            am_pm: finalTimeClass,
            corrected_time: finalTime
        };
        
        fetchEntry();
        
        try {
            await fetch('/api/vote', {
                method: 'POST',
                body: JSON.stringify(voteData),
                headers: { 'Content-Type': 'application/json' }
            });
            fetchStats();
        } catch (e) {
            console.error("Vote failed silently", e);
        }
    }
    
    function setTimeClass(val) {
        timeClass = val;
    }
    
    function setRating(val) {
        rating = val;
        hasVotedRating = true;
    }

    function formatTimeForInput(timeStr) {
        if (!timeStr) return '';
        // Ensure HH:MM format (pad hour with 0 if needed)
        const parts = timeStr.split(':');
        if (parts.length === 2) {
            return `${parts[0].padStart(2, '0')}:${parts[1]}`;
        }
        return timeStr;
    }

    onMount(() => {
        fetchStats();
        fetchEntry();
    });

    $: progress = stats.total_entries > 0 ? (stats.voted_entries / stats.total_entries) * 100 : 0;
</script>

<style>
    :global(.marked) {
        font-weight: 900;
        text-decoration: underline;
        color: #000;
        background-color: #fef08a;
        padding: 0 2px;
        border-radius: 2px;
    }
</style>

<div class="min-h-screen bg-gray-100 flex flex-col items-center p-4">
    <!-- Sticky Stats Bar -->
    <div class="sticky top-0 z-50 w-full max-w-md mb-4 bg-white rounded-xl shadow-md p-4 border-b-2 border-blue-500">
        <div class="flex justify-between text-sm font-bold text-gray-700 mb-2">
            <span>Progress: {stats.voted_entries} / {stats.total_entries}</span>
            <span>{progress.toFixed(2)}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-3 mb-2">
            <div class="bg-blue-600 h-3 rounded-full transition-all duration-500" style="width: {progress}%"></div>
        </div>
        <div class="flex justify-between items-center text-xs text-gray-500">
            <span>Avg Rating: <span class="font-bold text-yellow-600">{stats.average_rating.toFixed(1)} ★</span></span>
            <span class="italic">0 ★ = Denied</span>
        </div>
    </div>

    <div class="relative w-full max-w-md flex-1 mb-20" style="min-height: 500px;">
        {#if loading}
            <div class="absolute inset-0 flex items-center justify-center bg-white rounded-xl shadow-xl">
                <p class="text-gray-500 animate-pulse">Finding next quote...</p>
            </div>
        {:else if error}
             <div class="absolute inset-0 flex flex-col items-center justify-center bg-white rounded-xl shadow-xl p-6 text-center">
                <p class="text-red-500 mb-4 font-bold">{error}</p>
                <button on:click={fetchEntry} class="px-6 py-2 bg-blue-500 text-white rounded-lg shadow">Retry</button>
            </div>
        {:else if entry}
            <div in:fade={{ duration: 200 }} out:fly={{ x: -200, duration: 300 }} class="absolute inset-0 bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col">
                <!-- Card Header (Pinned) -->
                <div class="bg-gray-800 text-white p-4 text-center flex justify-between items-center shrink-0">
                    <div class="flex items-center">
                        {#if isEditingTime}
                            <input 
                                type="time" 
                                bind:value={correctedTime} 
                                class="bg-gray-700 text-white font-mono font-bold text-xl w-32 px-2 py-1 rounded border border-gray-500 focus:outline-none focus:border-blue-400 text-center"
                            />
                            <button on:click={() => isEditingTime = false} class="ml-2 text-gray-400 hover:text-white">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" /></svg>
                            </button>
                        {:else}
                            <button 
                                on:click={() => { isEditingTime = true; correctedTime = formatTimeForInput(entry.valid_times ? entry.valid_times[0] : ''); }} 
                                class="text-2xl font-mono font-bold hover:text-blue-300 transition-colors flex items-center gap-2 group"
                                title="Click to correct time"
                            >
                                {entry.valid_times ? entry.valid_times[0] : '??:??'}
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-0 group-hover:opacity-50 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                            </button>
                        {/if}
                    </div>
                    <a href={entry.link} target="_blank" class="text-xs text-blue-300 underline">View Source</a>
                </div>

                <!-- Scrollable Snippet Content (Middle) -->
                <div class="flex-1 p-6 overflow-y-auto flex flex-col justify-center bg-gray-50/30">
                    <div class="prose prose-lg text-gray-800 text-center leading-relaxed">
                        {@html entry.snippet}
                    </div>
                </div>

                <!-- Pinned Meta Info (Author, Title, Categories) -->
                <div class="p-4 border-t border-gray-100 bg-white shrink-0 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] z-10">
                    <div class="text-center mb-2">
                        <p class="font-bold text-gray-800 text-sm leading-tight">{entry.title}</p>
                        {#if entry.author}
                            <p class="text-xs text-gray-500 uppercase tracking-wide mt-1">{entry.author}</p>
                        {/if}
                    </div>

                    <!-- Categories -->
                    {#if entry.categories && entry.categories.length > 0}
                        <div class="flex flex-wrap gap-1 justify-center">
                            {#each entry.categories as cat}
                                <span class="px-2 py-0.5 bg-blue-50 text-blue-600 text-[10px] uppercase font-bold rounded-full border border-blue-100">
                                    {cat}
                                </span>
                            {/each}
                        </div>
                    {/if}
                </div>

                <!-- Controls (Pinned Bottom) -->
                <div class="bg-gray-50 p-4 border-t border-gray-200 space-y-6 shrink-0">
                    
                    <!-- Time Classification -->
                    <div class="grid grid-cols-3 gap-2">
                        {#each ['am', 'pm', 'ambiguous'] as t}
                            <button 
                                class="py-3 px-1 text-xs font-bold rounded-lg uppercase border-2 transition-all
                                {timeClass === t 
                                    ? 'border-blue-600 bg-blue-600 text-white shadow-inner scale-95' 
                                    : 'border-gray-200 bg-white text-gray-400 hover:border-gray-300'}"
                                on:click={() => setTimeClass(t)}
                            >
                                {t}
                            </button>
                        {/each}
                    </div>

                    <!-- Star Rating (Full Row) -->
                    <div class="flex justify-between items-center bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
                        <span class="text-xs font-bold text-gray-400 uppercase">Rating:</span>
                        <div class="flex space-x-2">
                            {#each [1, 2, 3, 4, 5] as star}
                                <button 
                                    on:click={() => setRating(star)}
                                    class="text-3xl focus:outline-none transition-transform active:scale-150"
                                >
                                    <span class={star <= rating ? 'text-yellow-400' : 'text-gray-200'}>★</span>
                                </button>
                            {/each}
                        </div>
                    </div>

                    <!-- Action Row -->
                    <div class="flex gap-2">
                        <button 
                            on:click={() => submitVote(true)}
                            class="flex-1 py-4 rounded-xl font-bold text-red-500 border-2 border-red-100 hover:bg-red-50 transition-all uppercase text-sm"
                        >
                            Deny
                        </button>
                        
                        <button 
                            on:click={() => submitVote(false)}
                            disabled={!hasVotedRating || !timeClass}
                            class="flex-[2] py-4 rounded-xl font-bold text-white transition-all shadow-lg text-sm uppercase
                            {!hasVotedRating || !timeClass 
                                ? 'bg-gray-300 cursor-not-allowed shadow-none' 
                                : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 transform active:scale-95'}"
                        >
                            Vote & Next
                        </button>
                    </div>
                </div>
            </div>
        {/if}
    </div>
</div>
