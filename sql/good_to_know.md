# SQLite - Good to know

## Memory Spaces and the corresponding space

1. Freelist pages
If "auto_vacuum" is enabled (1 or full)there won't be any freelist pages
2. Freeblocks
Free blocks in pages - if there are still allocated blocks in the page, there could be data in the freeblocks.
3. Page Unallocated Space
If "secure_delete" is enabled the content will be zeroed
4. Journal File   
Setting "journal_mode"
mostly done via "wal" today
A transferation into the sqlite occurs based on wal_auto_checkpoint (e.g. after size of 1000 pages ist reache )
When checkpoint occurs the wal isn't shrinked - so old data can live in the free pages of the wal

One needs to understand the transactions on the databases when e.g. inserting a new entry - otherwise it is difficult to make snese of the content of the wal.