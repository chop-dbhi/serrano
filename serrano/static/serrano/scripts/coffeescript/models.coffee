define ['underscore', 'backbone'], (_, Backbone) ->

    BRANCH_KEYS = ['children', 'type']
    CONDITION_KEYS = ['id', 'operator', 'value']
    LOGICAL_OPERATORS = ['and', 'or']

    class DataField extends Backbone.Model
        # Enables loading links provided by this resource. Pass in the name
        # of the link to asynchronously load the resource. Once loaded,
        # the data is locally cached. Pass `force` to reload the data from
        # the server.
        load: (name, callback, force=false) ->
            # Shift arguments
            if _.isBoolean(callback)
                force = callback
                callback = null
            if @[name]? and not force
                callback.apply @, @[name]
                return

            if not (link = @get('links')[name])
                throw new Error "No link '#{name}', links available
                    include: #{_.keys(@get 'links').join(', ')}"

            Backbone.ajax
                url: link.ref
                success: (json) =>
                    @[name] = json
                    callback.apply @, json


    class DataConcept extends Backbone.Model


    class Query extends Backbone.Model



    # Single condition node
    class ConditionNode extends Backbone.Model
        validate: (attrs) ->
            for key in CONDITION_KEYS
                if not attrs[key]?
                    return "Property #{key} is required"


    # Branch node
    class BranchNode extends Backbone.Model
        validate: (attrs) ->
            for key in BRANCH_KEYS
                if not attrs[key]?
                    return "Property #{key} is required"
            if attrs.children.length < 2
                return 'Branch nodes must contain two or more child nodes.'


    class Condition extends Backbone.Model
        set: (attrs) ->


    noConflict: ->


    # Instance
    session = new DataContextView

    { session }
