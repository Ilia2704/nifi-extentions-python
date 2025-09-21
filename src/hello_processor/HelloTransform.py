from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.relationship import Relationship
try:
    import hello              
except ImportError:
    from hello_processor import hello

class HelloTransform(FlowFileTransform):
    """
    Простой трансформер:
      - ставит атрибут greeting=Hello
      - контент: 'Hello' или 'Hello ' + исходный контент
    """

    class Java:
        implements = ['org.apache.nifi.python.processor.FlowFileTransform']

    class ProcessorDetails:
        version = "0.1.4"
        description = "Adds greeting=Hello and prefixes content with 'Hello ' (or sets 'Hello' if empty)."
        tags = ["hello", "python", "transform"]

    def __init__(self, jvm=None, **kwargs):
        self.jvm = jvm
        try:
            super().__init__() 
        except Exception:
            pass

    def getRelationships(self):
        return [
            Relationship(name="success", description="Processed successfully"),
            Relationship(name="failure", description="Processing failed"),
        ]

    def transform(self, context, flowfile):
        try:
            data = flowfile.getContentsAsBytes() or b""
            new_body, new_attrs = hello.transform(data)
            return FlowFileTransformResult(
                relationship="success",
                contents=new_body,
                attributes=new_attrs
            )
        except Exception as e:
            return FlowFileTransformResult(
                relationship="failure",
                contents=None,
                attributes={"error": str(e)[:512]}
            )
