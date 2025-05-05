<?php
/**
 * Plugin Name: Rank Math API Manager Extended v1.3
 * Description: Manages the update of Rank Math metadata (SEO Title, SEO Description, Canonical URL, Focus Keyword) via the REST API for WordPress posts and WooCommerce products. // Updated description
 * Version: 1.4 // Updated version
 * Author: Phil - https://inforeole.fr / Modified by AI Assistant
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit; // Exit if accessed directly.
}

class Rank_Math_API_Manager_Extended {
    public function __construct() {
        add_action('rest_api_init', [$this, 'register_meta_fields']);
        add_action('rest_api_init', [$this, 'register_api_routes']);
    }

    /**
     * Registers the Rank Math meta fields in the REST API for posts and products (if WooCommerce is active).
     */
    public function register_meta_fields() {
        $meta_fields = [
            'rank_math_title'           => 'SEO Title',
            'rank_math_description'     => 'SEO Description',
            'rank_math_canonical_url'   => 'Canonical URL',
            'rank_math_focus_keyword'   => 'Focus Keyword' // ADDED LINE
        ];

        // Register meta for posts by default.
        $post_types = ['post'];

        // If WooCommerce is active, add the 'product' post type.
        if ( class_exists('WooCommerce') ) {
            $post_types[] = 'product';
        }

        foreach ( $post_types as $post_type ) {
            foreach ( $meta_fields as $key => $description ) {
                register_post_meta( $post_type, $key, [
                    'show_in_rest'   => true, // Might help standard API, but not guaranteed
                    'single'         => true,
                    'type'           => 'string',
                    'auth_callback'  => [$this, 'check_update_permission'],
                    'description'    => $description,
                ] );
            }
        }
    }

    /**
     * Registers the REST API route to update Rank Math meta fields.
     */
    public function register_api_routes() {
        register_rest_route( 'rank-math-api/v1', '/update-meta', [
            'methods'             => 'POST',
            'callback'            => [$this, 'update_rank_math_meta'],
            'permission_callback' => [$this, 'check_update_permission'],
            'args'                => [
                'post_id' => [
                    'required'          => true,
                    'validate_callback' => function( $param ) {
                        return is_numeric( $param ) && get_post( $param );
                    }
                ],
                'rank_math_title' => [
                    'type'              => 'string',
                    'sanitize_callback' => 'sanitize_text_field',
                ],
                'rank_math_description' => [
                    'type'              => 'string',
                    'sanitize_callback' => 'sanitize_text_field',
                ],
                'rank_math_canonical_url' => [
                    'type'              => 'string',
                    'sanitize_callback' => 'esc_url_raw',
                ],
                // ADDED ARGUMENT for Focus Keyword
                'rank_math_focus_keyword' => [
                    'type'              => 'string',
                    'sanitize_callback' => 'sanitize_text_field', // Simple sanitization, Rank Math might do more internally
                ],
            ],
        ] );
    }

    /**
     * Updates the Rank Math meta fields via the REST API.
     */
    public function update_rank_math_meta( WP_REST_Request $request ) {
        $post_id = $request->get_param( 'post_id' );
        // ADDED 'rank_math_focus_keyword' to the fields array
        $fields  = ['rank_math_title', 'rank_math_description', 'rank_math_canonical_url', 'rank_math_focus_keyword'];
        $result  = [];

        foreach ( $fields as $field ) {
            $value = $request->get_param( $field );
            // Check if the parameter was actually passed in the request
            if ( $value !== null ) {
                // Use update_post_meta to save the value
                $update_result = update_post_meta( $post_id, $field, $value );
                // Report status for the specific field
                $result[ $field ] = $update_result ? 'updated' : 'failed_or_unchanged';
            } else {
                 $result[ $field ] = 'not_provided'; // Indicate if a field wasn't sent
            }
        }

        // Check if any field was actually attempted to be updated
        $attempted_updates = array_filter($result, function($status) {
            return $status !== 'not_provided';
        });

        if ( empty( $attempted_updates ) ) {
            return new WP_Error( 'no_fields_provided', 'No metadata fields were provided in the request', ['status' => 400] );
        }
        
        // Check if any update succeeded
        $successful_updates = array_filter($result, function($status) {
             return $status === 'updated';
        });

        if ( empty( $successful_updates ) ) {
             // Return success=false if no fields were actually updated (all failed or were unchanged)
             // Keep status 200 OK, but indicate failure in the response body
             return new WP_REST_Response( ['success' => false, 'message' => 'No metadata fields were successfully updated (check values or permissions).', 'details' => $result], 200 );
        }


        // Return success=true if at least one field was updated
        return new WP_REST_Response( ['success' => true, 'message' => 'Metadata update attempted.', 'details' => $result], 200 );
    }

    /**
     * Checks if the current user has permission to update the meta fields.
     */
    public function check_update_permission() {
        // Ensure the user has the capability to edit the specific post type
        // This is a more robust check than just 'edit_posts'
        $post_id = isset($_REQUEST['post_id']) ? (int)$_REQUEST['post_id'] : 0;
        if ( $post_id > 0 ) {
             $post_type = get_post_type($post_id);
             if ( $post_type ) {
                 $post_type_object = get_post_type_object( $post_type );
                 if ( $post_type_object ) {
                     return current_user_can( $post_type_object->cap->edit_post, $post_id );
                 }
             }
        }
        // Fallback or if post_id isn't available early
        return current_user_can( 'edit_posts' );
    }
}

new Rank_Math_API_Manager_Extended();