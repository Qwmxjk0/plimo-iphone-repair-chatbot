# Unit / contract tests — 2026-10-15 08:39 (เวลาไทย)

รันใน API container ด้วย `python -m unittest` (OpenAI, LightRAG และ Stripe เป็น mock; Redis integration ใช้ Redis จริงด้วย key prefix แยก) ไม่มีค่าใช้จ่าย API

```
test_general_duration_question_is_not_case_tracking (test_logic.CaseReferenceTests.test_general_duration_question_is_not_case_tracking) ... ok
test_not_a_reference (test_logic.CaseReferenceTests.test_not_a_reference) ... ok
test_reference_formats (test_logic.CaseReferenceTests.test_reference_formats) ... ok
test_exact_prices (test_logic.CatalogTests.test_exact_prices) ... ok
test_out_of_range_and_unknown_service (test_logic.CatalogTests.test_out_of_range_and_unknown_service) ... ok
test_totals_differences_and_cables (test_logic.CatalogTests.test_totals_differences_and_cables) ... ok
test_validator (test_logic.CatalogTests.test_validator) ... ok
test_variants_never_get_base_price (test_logic.CatalogTests.test_variants_never_get_base_price) ... ok
test_model_aliases_and_variants (test_logic.EntityTests.test_model_aliases_and_variants) ... ok
test_same_question_spellings_share_one_key (test_logic.EntityTests.test_same_question_spellings_share_one_key) ... ok
test_services (test_logic.EntityTests.test_services) ... ok
test_explicit_case_number_forces_case_route (test_logic.RouterParseTests.test_explicit_case_number_forces_case_route) ... ok
test_explicit_message_facts_override_model (test_logic.RouterParseTests.test_explicit_message_facts_override_model) ... ok
test_follow_up_keeps_carried_over_model_and_services (test_logic.RouterParseTests.test_follow_up_keeps_carried_over_model_and_services) ... ok
test_invalid_values_are_sanitized (test_logic.RouterParseTests.test_invalid_values_are_sanitized) ... ok
test_rules_fallback (test_logic.RouterParseTests.test_rules_fallback) ... ok
test_second_shop_question_is_not_dropped (test_logic.RouterParseTests.test_second_shop_question_is_not_dropped) ... ok
test_cards_masked_but_not_imei_or_phone (test_logic.SensitiveDataTests.test_cards_masked_but_not_imei_or_phone) ... ok
test_contact_details_detected (test_logic.SensitiveDataTests.test_contact_details_detected) ... ok
test_injection_markers_are_precise (test_logic.SensitiveDataTests.test_injection_markers_are_precise) ... ok
test_national_id (test_logic.SensitiveDataTests.test_national_id) ... ok
test_images_analyzed_before_retrieval_and_session_isolation (test_chat.ChatTests.test_images_analyzed_before_retrieval_and_session_isolation) ... 2026-10-15 01:39:32,271 INFO plimo chat_complete route=shop_info timings={'router_ms': 1, 'vision_ms': 0, 'retrieval_ms': 0, 'generation_ms': 0, 'total_ms': 3} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_invalid_image_rejected_before_provider_call (test_chat.ChatTests.test_invalid_image_rejected_before_provider_call) ... ok
test_missing_context_skips_answer_model (test_chat.ChatTests.test_missing_context_skips_answer_model) ... 2026-10-15 01:39:32,304 INFO plimo chat_complete route=shop_info timings={'router_ms': 1, 'retrieval_ms': 0, 'total_ms': 1} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_no_key_does_not_fake_rag (test_chat.ChatTests.test_no_key_does_not_fake_rag) ... ok
test_provider_error_releases_lock_and_returns_error (test_chat.ChatTests.test_provider_error_releases_lock_and_returns_error) ... 2026-10-15 01:39:32,310 WARNING plimo router_fallback type=HTTPStatusError
test_readiness_detects_redis_failure (test_chat.ChatTests.test_readiness_detects_redis_failure) ... ok
test_suffix_folding_preserves_meaningful_details (test_chat.ChatTests.test_suffix_folding_preserves_meaningful_details) ... ok
test_text_routes_retrieves_generates_and_repeats_hit_fast_cache (test_chat.ChatTests.test_text_routes_retrieves_generates_and_repeats_hit_fast_cache) ... 2026-10-15 01:39:32,318 INFO plimo chat_complete route=shop_info timings={'router_ms': 1, 'retrieval_ms': 0, 'generation_ms': 0, 'total_ms': 1} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_thai_suffix_variations_reuse_answer_without_upstream_calls (test_chat.ChatTests.test_thai_suffix_variations_reuse_answer_without_upstream_calls) ... 2026-10-15 01:39:32,325 INFO plimo chat_complete route=shop_info timings={'router_ms': 1, 'retrieval_ms': 0, 'generation_ms': 0, 'total_ms': 1} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_budget_exhausted_keeps_cached_answers_and_blocks_new_calls (test_chat.FlowTests.test_budget_exhausted_keeps_cached_answers_and_blocks_new_calls) ... 2026-10-15 01:39:32,334 INFO plimo chat_complete route=shop_info timings={'router_ms': 1, 'retrieval_ms': 0, 'generation_ms': 0, 'total_ms': 1} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_card_number_never_leaves_the_api (test_chat.FlowTests.test_card_number_never_leaves_the_api) ... 2026-10-15 01:39:32,340 INFO plimo chat_complete route=guard_card timings={'total_ms': 0} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=['card']
test_catalog_amounts_and_totals_pass_validation (test_chat.FlowTests.test_catalog_amounts_and_totals_pass_validation) ... 2026-10-15 01:39:32,343 INFO plimo chat_complete route=price timings={'router_ms': 1, 'retrieval_ms': 0, 'generation_ms': 0, 'total_ms': 1} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_follow_up_is_rewritten_with_context (test_chat.FlowTests.test_follow_up_is_rewritten_with_context) ... 2026-10-15 01:39:32,346 WARNING plimo answer_blocked reason=price
test_guest_session_rate_limit (test_chat.FlowTests.test_guest_session_rate_limit) ... 2026-10-15 01:39:32,352 INFO plimo chat_complete route=shop_info timings={'router_ms': 1, 'retrieval_ms': 0, 'generation_ms': 0, 'total_ms': 1} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_injection_pattern_refused_without_model (test_chat.FlowTests.test_injection_pattern_refused_without_model) ... 2026-10-15 01:39:32,359 INFO plimo chat_complete route=unsafe timings={'total_ms': 0} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=['injection']
test_leaked_internal_markers_are_replaced (test_chat.FlowTests.test_leaked_internal_markers_are_replaced) ... 2026-10-15 01:39:32,362 WARNING plimo answer_blocked reason=leak
test_national_id_masked_before_router (test_chat.FlowTests.test_national_id_masked_before_router) ... 2026-10-15 01:39:32,366 INFO plimo chat_complete route=shop_info timings={'router_ms': 1, 'retrieval_ms': 0, 'generation_ms': 0, 'total_ms': 1} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=['national_id']
test_out_of_scope_gets_fixed_reply_without_generation (test_chat.FlowTests.test_out_of_scope_gets_fixed_reply_without_generation) ... 2026-10-15 01:39:32,368 INFO plimo chat_complete route=out_of_scope timings={'router_ms': 1, 'total_ms': 1} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_paraphrases_share_one_answer_across_users (test_chat.FlowTests.test_paraphrases_share_one_answer_across_users) ... 2026-10-15 01:39:32,373 INFO plimo chat_complete route=price timings={'router_ms': 1, 'retrieval_ms': 0, 'generation_ms': 0, 'total_ms': 2} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_shared_answer_never_contains_another_users_details (test_chat.FlowTests.test_shared_answer_never_contains_another_users_details) ... 2026-10-15 01:39:32,379 INFO plimo chat_complete route=price timings={'router_ms': 1, 'retrieval_ms': 0, 'generation_ms': 0, 'total_ms': 2} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_single_flight_runs_compute_once (test_chat.FlowTests.test_single_flight_runs_compute_once) ... ok
test_time_sensitive_question_gets_date_and_no_fast_cache (test_chat.FlowTests.test_time_sensitive_question_gets_date_and_no_fast_cache) ... 2026-10-15 01:39:32,906 INFO plimo chat_complete route=shop_info timings={'router_ms': 2, 'retrieval_ms': 1, 'generation_ms': 0, 'total_ms': 3} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_usage_is_metered_per_call (test_chat.FlowTests.test_usage_is_metered_per_call) ... 2026-10-15 01:39:32,918 INFO plimo chat_complete route=shop_info timings={'router_ms': 1, 'retrieval_ms': 1, 'generation_ms': 0, 'total_ms': 3} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_validator_blocks_base_price_for_pro_max (test_chat.FlowTests.test_validator_blocks_base_price_for_pro_max) ... 2026-10-15 01:39:32,922 WARNING plimo answer_blocked reason=price
test_case_chat_reads_fresh_owned_status_without_openai (test_membership.MemberTests.test_case_chat_reads_fresh_owned_status_without_openai) ... 2026-10-15 01:39:33,474 INFO plimo chat_complete route=case timings={'total_ms': 9} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_case_lifecycle_counts_and_audit (test_membership.MemberTests.test_case_lifecycle_counts_and_audit) ... ok
test_chat_persists_and_isolated_across_members (test_membership.MemberTests.test_chat_persists_and_isolated_across_members) ... 2026-10-15 01:39:34,732 INFO plimo chat_complete route=shop_info timings={'router_ms': 0, 'retrieval_ms': 0, 'generation_ms': 0, 'total_ms': 3} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_fresh_demo_seed_has_pending_quote_and_is_idempotent (test_membership.MemberTests.test_fresh_demo_seed_has_pending_quote_and_is_idempotent) ... Created 2 demo accounts, 3 example conversations, 8 example cases. No AI calls.
test_ownership_and_admin_permissions (test_membership.MemberTests.test_ownership_and_admin_permissions) ... ok
test_quote_approval_ownership_and_price_guard (test_membership.MemberTests.test_quote_approval_ownership_and_price_guard) ... ok
test_quote_revision_reject_and_stale_decision (test_membership.MemberTests.test_quote_revision_reject_and_stale_decision) ... ok
test_roles_logout_and_csrf (test_membership.MemberTests.test_roles_logout_and_csrf) ... ok
test_chat_reports_payment_from_database_only (test_payments.PaymentTests.test_chat_reports_payment_from_database_only) ... 2026-10-15 01:39:38,148 INFO plimo chat_complete route=case timings={'total_ms': 4} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_checkout_uses_server_amount_and_reuses_pending_session (test_payments.PaymentTests.test_checkout_uses_server_amount_and_reuses_pending_session) ... 2026-10-15 01:39:38,779 INFO plimo.payments checkout_created case=1 quote=1
test_confirm_asks_stripe_and_is_idempotent (test_payments.PaymentTests.test_confirm_asks_stripe_and_is_idempotent) ... 2026-10-15 01:39:39,322 INFO plimo.payments checkout_created case=1 quote=1
test_live_keys_and_live_sessions_are_refused (test_payments.PaymentTests.test_live_keys_and_live_sessions_are_refused) ... 2026-10-15 01:39:39,884 ERROR plimo.payments stripe_session_rejected livemode=True
test_mismatched_session_is_not_marked_paid (test_payments.PaymentTests.test_mismatched_session_is_not_marked_paid) ... 2026-10-15 01:39:40,423 INFO plimo.payments checkout_created case=1 quote=1
test_only_owner_and_only_approved_quote (test_payments.PaymentTests.test_only_owner_and_only_approved_quote) ... ok
test_paid_case_cannot_be_requoted_or_cancelled (test_payments.PaymentTests.test_paid_case_cannot_be_requoted_or_cancelled) ... 2026-10-15 01:39:41,497 INFO plimo.payments checkout_created case=1 quote=1
test_webhook_signature_timestamp_and_duplicates (test_payments.PaymentTests.test_webhook_signature_timestamp_and_duplicates) ... 2026-10-15 01:39:42,054 INFO plimo.payments checkout_created case=1 quote=1
test_all_cache_layers_ttls_and_locks (test_redis_integration.RedisIntegration.test_all_cache_layers_ttls_and_locks) ... 2026-10-15 01:39:42,098 INFO plimo chat_complete route=shop_info timings={'router_ms': 2, 'vision_ms': 1, 'retrieval_ms': 1, 'generation_ms': 1, 'total_ms': 9} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_images_analyzed_before_retrieval_and_session_isolation (test_redis_integration.RedisIntegration.test_images_analyzed_before_retrieval_and_session_isolation) ... 2026-10-15 01:39:42,178 INFO plimo chat_complete route=shop_info timings={'router_ms': 2, 'vision_ms': 1, 'retrieval_ms': 1, 'generation_ms': 1, 'total_ms': 7} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_invalid_image_rejected_before_provider_call (test_redis_integration.RedisIntegration.test_invalid_image_rejected_before_provider_call) ... ok
test_lock_release_does_not_delete_replacement (test_redis_integration.RedisIntegration.test_lock_release_does_not_delete_replacement) ... 2026-10-15 01:39:42,221 INFO plimo chat_complete route=shop_info timings={'router_ms': 8, 'retrieval_ms': 0, 'generation_ms': 6, 'total_ms': 17} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_missing_context_skips_answer_model (test_redis_integration.RedisIntegration.test_missing_context_skips_answer_model) ... 2026-10-15 01:39:42,240 INFO plimo chat_complete route=shop_info timings={'router_ms': 2, 'retrieval_ms': 0, 'total_ms': 5} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_no_key_does_not_fake_rag (test_redis_integration.RedisIntegration.test_no_key_does_not_fake_rag) ... ok
test_provider_error_releases_lock_and_returns_error (test_redis_integration.RedisIntegration.test_provider_error_releases_lock_and_returns_error) ... 2026-10-15 01:39:42,263 WARNING plimo router_fallback type=HTTPStatusError
test_rate_limit_and_existing_lock (test_redis_integration.RedisIntegration.test_rate_limit_and_existing_lock) ... 2026-10-15 01:39:42,305 INFO plimo chat_complete route=shop_info timings={'router_ms': 3, 'retrieval_ms': 0, 'generation_ms': 1, 'total_ms': 7} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_readiness_detects_redis_failure (test_redis_integration.RedisIntegration.test_readiness_detects_redis_failure) ... ok
test_suffix_folding_preserves_meaningful_details (test_redis_integration.RedisIntegration.test_suffix_folding_preserves_meaningful_details) ... ok
test_text_routes_retrieves_generates_and_repeats_hit_fast_cache (test_redis_integration.RedisIntegration.test_text_routes_retrieves_generates_and_repeats_hit_fast_cache) ... 2026-10-15 01:39:42,347 INFO plimo chat_complete route=shop_info timings={'router_ms': 3, 'retrieval_ms': 0, 'generation_ms': 1, 'total_ms': 5} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_thai_suffix_variations_reuse_answer_without_upstream_calls (test_redis_integration.RedisIntegration.test_thai_suffix_variations_reuse_answer_without_upstream_calls) ... 2026-10-15 01:39:42,372 INFO plimo chat_complete route=shop_info timings={'router_ms': 8, 'retrieval_ms': 0, 'generation_ms': 1, 'total_ms': 11} cache={'fast': False, 'router': False, 'answer': False, 'retrieval': False, 'vision': False} guard=[]
test_demo_only_with_explicit_option_and_label (test_ingest.IngestTests.test_demo_only_with_explicit_option_and_label) ... ok
test_estimates_are_indexed_without_demo_opt_in (test_ingest.IngestTests.test_estimates_are_indexed_without_demo_opt_in) ... ok
Ran 75 tests in 10.146s
OK
```
